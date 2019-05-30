import json
import logging
import time

import docker
from flask import Flask

from titus_isolate import log
from titus_isolate.api.testing import is_testing
from titus_isolate.cgroup.file_cgroup_manager import FileCgroupManager
from titus_isolate.config.constants import TITUS_ISOLATE_BLOCK_SEC, DEFAULT_TITUS_ISOLATE_BLOCK_SEC, RESTART_PROPERTIES
from titus_isolate.config.restart_property_watcher import RestartPropertyWatcher
from titus_isolate.event.create_event_handler import CreateEventHandler
from titus_isolate.event.event_manager import EventManager
from titus_isolate.event.free_event_handler import FreeEventHandler
from titus_isolate.event.rebalance_event_handler import RebalanceEventHandler
from titus_isolate.event.reconcile_event_handler import ReconcileEventHandler
from titus_isolate.event.utils import get_current_workloads
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.reconciler import Reconciler
from titus_isolate.isolate.utils import get_fallback_allocator
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.keystone_event_log_manager import KeystoneEventLogManager
from titus_isolate.metrics.metrics_manager import MetricsManager
from titus_isolate.model.processor.config import get_cpu_from_env
from titus_isolate.monitor.workload_monitor_manager import WorkloadMonitorManager
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager
from titus_isolate.real_exit_handler import RealExitHandler
from titus_isolate.utils import get_config_manager, get_workload_manager, get_event_manager, \
    get_workload_monitor_manager, set_event_log_manager, start_periodic_scheduling, set_cpu_usage_predictor_manager, \
    set_workload_monitor_manager, set_workload_manager, set_event_manager

app = Flask(__name__)


@app.route('/isolate/<workload_id>')
def isolate_workload(workload_id, timeout=None):
    if timeout is None:
        timeout = get_config_manager().get_float(TITUS_ISOLATE_BLOCK_SEC, DEFAULT_TITUS_ISOLATE_BLOCK_SEC)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if get_workload_manager().is_isolated(workload_id):
            return json.dumps({'workload_id': workload_id}), 200, {'ContentType': 'application/json'}
        time.sleep(0.1)

    log.error("Failed to isolate workload: '{}'".format(workload_id))
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
        "event_manager": {
            "queue_depth": get_event_manager().get_queue_depth(),
            "success_count": get_event_manager().get_success_count(),
            "error_count": get_event_manager().get_error_count(),
            "processed_count": get_event_manager().get_processed_count()
        },
        "workload_manager": {
            "cpu_allocator": get_workload_manager().get_allocator_name(),
            "workload_count": len(get_workload_manager().get_workloads()),
            "isolated_workload_count": len(get_workload_manager().get_isolated_workload_ids()),
            "success_count": get_workload_manager().get_success_count(),
            "error_count": get_workload_manager().get_error_count(),
            "added_count": get_workload_manager().get_added_count(),
            "removed_count": get_workload_manager().get_removed_count()
        }
    })


@app.route('/metrics/raw')
def get_metrics():
    return json.dumps(get_workload_monitor_manager().to_dict())


@app.route('/metrics/cpu_usage/<workload_id>/<seconds>/<granularity>')
def get_cpu_usage(workload_id, seconds, granularity):
    cpu_usage = get_workload_monitor_manager().get_cpu_usage(seconds, granularity)

    if workload_id.lower() == 'all':
        return json.dumps(cpu_usage)

    if workload_id in cpu_usage:
        return json.dumps(cpu_usage[workload_id])

    return json.dumps({'unknown_workload_id': workload_id}), 404, {'ContentType': 'application/json'}


if __name__ != '__main__' and not is_testing():
    log.info("Configuring logging...")
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    # Set the schedule library's logging level higher so it doesn't spam messages every time it schedules a task
    logging.getLogger('schedule').setLevel(logging.WARN)

    exit_handler = RealExitHandler()

    log.info("Setting event log manager...")
    event_log_manager = KeystoneEventLogManager()
    set_event_log_manager(event_log_manager)

    log.info("Watching property changes for restart...")
    RestartPropertyWatcher(get_config_manager(), exit_handler, RESTART_PROPERTIES)

    log.info("Modeling the CPU...")
    cpu = get_cpu_from_env()

    # Start period scheduling
    log.info("Starting periodic event scheduling...")
    start_periodic_scheduling()

    # Start the cpu usage predictor manager
    log.info("Setting up the cpu usage predictor manager...")
    cpu_predictor_manager = CpuUsagePredictorManager()
    set_cpu_usage_predictor_manager(cpu_predictor_manager)

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
    log.info("Setting up the Docker event handlers...")
    create_event_handler = CreateEventHandler(workload_manager)
    free_event_handler = FreeEventHandler(workload_manager)
    rebalance_event_handler = RebalanceEventHandler(workload_manager)
    reconciler = Reconciler(cgroup_manager, RealExitHandler())
    reconcile_event_handler = ReconcileEventHandler(reconciler)
    event_handlers = [create_event_handler, free_event_handler, rebalance_event_handler, reconcile_event_handler]

    # Start event processing
    log.info("Starting Docker event handling...")
    event_manager = EventManager(docker.from_env().events(), event_handlers)
    set_event_manager(event_manager)

    # Report metrics
    log.info("Starting metrics reporting...")
    MetricsManager([
        cgroup_manager,
        event_log_manager,
        event_manager,
        reconciler,
        workload_manager,
        workload_monitor_manager])

    # Initialize currently running containers as workloads
    log.info("Isolating currently running workloads...")
    for workload in get_current_workloads(docker.from_env()):
        try:
            workload_manager.add_workload(workload)
        except:
            log.exception("Failed to add currently running workload: '{}', maybe it exited.".format(workload.get_id()))

    # Start processing events after adding running workloads to avoid processing a die event before we add a workload
    event_manager.start_processing_events()
