import json
import logging
import threading
import time

import docker
from flask import Flask

from titus_isolate import log
from titus_isolate.api.testing import is_testing
from titus_isolate.cgroup.file_cgroup_manager import FileCgroupManager
from titus_isolate.config.constants import RESTART_PROPERTIES
from titus_isolate.config.restart_property_watcher import RestartPropertyWatcher
from titus_isolate.event.create_event_handler import CreateEventHandler
from titus_isolate.event.event_manager import EventManager
from titus_isolate.event.free_event_handler import FreeEventHandler
from titus_isolate.event.kubernetes_opportunistic_window_publisher import KubernetesOpportunisticWindowPublisher
from titus_isolate.event.rebalance_event_handler import RebalanceEventHandler
from titus_isolate.event.reconcile_event_handler import ReconcileEventHandler
from titus_isolate.event.oversubscribe_event_handler import OversubscribeEventHandler
from titus_isolate.event.utils import get_current_workloads
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.reconciler import Reconciler
from titus_isolate.isolate.utils import get_fallback_allocator
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import ISOLATE_LATENCY_KEY
from titus_isolate.metrics.keystone_event_log_manager import KeystoneEventLogManager
from titus_isolate.metrics.metrics_manager import MetricsManager, registry
from titus_isolate.model.processor.config import get_cpu_from_env
from titus_isolate.monitor.workload_monitor_manager import WorkloadMonitorManager
from titus_isolate.pod.pod_manager import PodManager
from titus_isolate.predict.cpu_usage_predictor_manager import ConfigurableCpuUsagePredictorManager
from titus_isolate.real_exit_handler import RealExitHandler
from titus_isolate.utils import get_config_manager, get_workload_manager, \
    set_event_log_manager, start_periodic_scheduling, set_cpu_usage_predictor_manager, \
    set_workload_monitor_manager, set_workload_manager, set_event_manager, is_kubernetes, \
    set_pod_manager, is_running_on_agent

app = Flask(__name__)

metrics_manager = None
__isolate_latency = {}
__isolate_lock = threading.Lock()


@app.route('/isolate/<workload_id>')
def isolate_workload(workload_id):
    # We acquire a lock here to serialize callers and protect against contention with actual isolation work.
    if not __isolate_lock.acquire(timeout=0.1):
        log.warn("timeout getting isolate lock for workload: {}".format(workload_id))
        return json.dumps({'workload_id': workload_id}), 404, {'ContentType': 'application/json'}

    start_time = time.time()

    if get_workload_manager().is_isolated(workload_id):
        stop_time = time.time()
        if metrics_manager is not None:
            start_time = __isolate_latency.pop(workload_id, start_time)
            duration = stop_time - start_time
            registry.distribution_summary(ISOLATE_LATENCY_KEY, metrics_manager.get_tags()).record(duration)

        __isolate_lock.release()
        log.info("workload: '{}' IS isolated".format(workload_id))
        return json.dumps({'workload_id': workload_id}), 200, {'ContentType': 'application/json'}

    log.info("workload: '{}' is NOT isolated".format(workload_id))
    if workload_id not in __isolate_latency:
        __isolate_latency[workload_id] = time.time()

    __isolate_lock.release()
    return json.dumps({'unknown_workload_id': workload_id}), 404, {'ContentType': 'application/json'}


@app.route('/workloads')
def get_workloads():
    workloads = [w.to_dict() for w in get_workload_manager().get_workloads()]
    return json.dumps(workloads)


@app.route('/isolated_workload_ids')
def get_isolated_workload_ids():
    return json.dumps(list(get_workload_manager().get_isolated_workload_ids()))


@app.route('/cpu')
def get_cpu():
    return json.dumps(get_workload_manager().get_cpu().to_dict())


@app.route('/violations')
def get_violations():
    return json.dumps({
        "cross_package": get_cross_package_violations(get_workload_manager().get_cpu()),
        "shared_core": get_shared_core_violations(get_workload_manager().get_cpu())
    })


@app.route('/status')
def get_wm_status():
    return json.dumps({
        "workload_manager": {
            "cpu_allocator": get_workload_manager().get_allocator_name(),
            "workload_count": len(get_workload_manager().get_workloads()),
            "isolated_workload_count": len(get_workload_manager().get_isolated_workload_ids())
        }
    })


def _notify_ready():
    if is_running_on_agent():
        from systemd import daemon
        from systemd.daemon import Notification
        daemon.notify(Notification.READY)


def init():
    # Initialize currently running containers as workloads
    log.info("Isolating currently running workloads...")
    for workload in get_current_workloads(docker.from_env()):
        try:
            workload_manager.add_workload(workload)
        except:
            log.exception("Failed to add currently running workload: '{}', maybe it exited.".format(workload.get_id()))

    log.info("Isolated currently running workloads.")
    # Start processing events after adding running workloads to avoid processing a die event before we add a workload
    event_manager.start_processing_events()
    _notify_ready()


if __name__ != '__main__' and not is_testing():
    log.info("Configuring logging...")
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    # Set the schedule library's logging level higher so it doesn't spam messages every time it schedules a task
    logging.getLogger('schedule').setLevel(logging.WARN)

    exit_handler = RealExitHandler()

    if is_kubernetes():
        log.info("Setting pod manager...")
        pod_manager = PodManager()
        pod_manager.start()
        set_pod_manager(pod_manager)

    log.info("Setting event log manager...")
    event_log_manager = KeystoneEventLogManager()
    set_event_log_manager(event_log_manager)

    log.info("Watching property changes for restart...")
    RestartPropertyWatcher(get_config_manager(), exit_handler, RESTART_PROPERTIES)

    log.info("Modeling the CPU...")
    cpu = get_cpu_from_env()

    # Start periodic scheduling
    log.info("Starting periodic event scheduling...")
    start_periodic_scheduling(exit_handler)

    # Start the cpu usage predictor manager
    log.info("Setting up the cpu usage predictor manager...")
    set_cpu_usage_predictor_manager(ConfigurableCpuUsagePredictorManager())

    # Start performance monitoring
    log.info("Starting performance monitoring...")
    workload_monitor_manager = WorkloadMonitorManager()
    set_workload_monitor_manager(workload_monitor_manager)

    # Setup the workload manager
    log.info("Setting up the workload manager...")
    cpu_allocator = get_fallback_allocator(get_config_manager())
    log.info("Created Fallback CPU allocator with primary: '{}' and secondary: '{}".format(
        cpu_allocator.get_primary_allocator().__class__.__name__,
        cpu_allocator.get_secondary_allocator().__class__.__name__))
    cgroup_manager = FileCgroupManager()
    workload_manager = WorkloadManager(cpu=cpu, cgroup_manager=cgroup_manager, cpu_allocator=cpu_allocator)
    set_workload_manager(workload_manager)

    # Setup the event handlers
    log.info("Setting up event handlers...")
    reconciler = Reconciler(cgroup_manager, RealExitHandler())
    create_event_handler = CreateEventHandler(workload_manager)
    free_event_handler = FreeEventHandler(workload_manager)
    rebalance_event_handler = RebalanceEventHandler(workload_manager)
    reconcile_event_handler = ReconcileEventHandler(reconciler)
    oversub_event_handler = None
    if is_kubernetes():
        oversub_event_handler = OversubscribeEventHandler(workload_manager,
                                                          KubernetesOpportunisticWindowPublisher(exit_handler))

    event_handlers = [h for h in [create_event_handler,
                                  free_event_handler,
                                  rebalance_event_handler,
                                  reconcile_event_handler,
                                  oversub_event_handler] if h is not None]

    # Start event processing
    log.info("Starting Docker event handling...")
    event_manager = EventManager(docker.from_env().events(), event_handlers)
    set_event_manager(event_manager)

    # Report metrics
    log.info("Starting metrics reporting...")
    metrics_reporters = [m for m in [cgroup_manager,
                                     event_log_manager,
                                     event_manager,
                                     reconciler,
                                     workload_manager,
                                     workload_monitor_manager,
                                     oversub_event_handler] if m is not None]

    metrics_manager = MetricsManager(metrics_reporters)

    threading.Thread(target=init).start()


