import os
import time
from threading import Thread, Lock

import grpc
import requests
import schedule

from titus_isolate import log
from titus_isolate.allocate.constants import TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL
from titus_isolate.allocate.remote.isolate_pb2 import CurrentCellRequest
from titus_isolate.allocate.remote.isolate_pb2_grpc import IsolationServiceStub
from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, REMOTE_ALLOCATOR_URL, GRPC_REMOTE_ALLOC_ENDPOINT, \
    MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME
from titus_isolate.constants import KUBERNETES_BACKEND_KEY, SCHEDULE_ONCE_FAILURE_EXIT_CODE, \
    SCHEDULING_LOOP_FAILURE_EXIT_CODE
from titus_isolate.exit_handler import ExitHandler

SCHEDULING_SLEEP_INTERVAL = 10.0

scheduling_lock = Lock()
scheduling_started = False

config_manager_lock = Lock()
__config_manager = None

workload_manager_lock = Lock()
__workload_manager = None

event_manager_lock = Lock()
__event_manager = None

event_log_manager_lock = Lock()
__event_log_manager = None

workload_monitor_manager_lock = Lock()
__workload_monitor_manager = None

cpu_usage_predictor_manager_lock = Lock()
__cpu_usage_predictor_manager = None

pod_manager_lock = Lock()
__pod_manager = None

__managers = [
    __config_manager,
    __workload_manager,
    __event_manager,
    __event_log_manager,
    __workload_monitor_manager,
    __pod_manager
]


def managers_are_initialized() -> bool:
    unset_managers = [m for m in __managers if m is None]
    return len(unset_managers) > 0


def get_config_manager(property_provider=AgentPropertyProvider()):
    global __config_manager

    with config_manager_lock:
        if __config_manager is None:
            __config_manager = ConfigManager(property_provider)

        return __config_manager


def set_config_manager(config_manager):
    global __config_manager

    with config_manager_lock:
        __config_manager = config_manager


def get_workload_manager():
    global __workload_manager

    with workload_manager_lock:
        return __workload_manager


def set_workload_manager(workload_manager):
    global __workload_manager

    with workload_manager_lock:
        __workload_manager = workload_manager


def get_event_manager():
    global __event_manager

    with event_manager_lock:
        return __event_manager


def set_event_manager(event_manager):
    global __event_manager

    with event_manager_lock:
        __event_manager = event_manager


def get_event_log_manager():
    global __event_log_manager

    with event_log_manager_lock:
        return __event_log_manager


def set_event_log_manager(event_log_manager):
    global __event_log_manager

    with event_log_manager_lock:
        __event_log_manager = event_log_manager


def set_workload_monitor_manager(workoad_monitor_manager):
    global __workload_monitor_manager

    with workload_monitor_manager_lock:
        __workload_monitor_manager = workoad_monitor_manager


def get_workload_monitor_manager():
    global __workload_monitor_manager

    with workload_monitor_manager_lock:
        return __workload_monitor_manager


def set_cpu_usage_predictor_manager(cpu_usage_predictor_manager):
    global __cpu_usage_predictor_manager

    with cpu_usage_predictor_manager_lock:
        __cpu_usage_predictor_manager = cpu_usage_predictor_manager


def get_cpu_usage_predictor_manager():
    global __cpu_usage_predictor_manager

    with cpu_usage_predictor_manager_lock:
        return __cpu_usage_predictor_manager


def set_pod_manager(pod_manager):
    global __pod_manager

    with pod_manager_lock:
        __pod_manager = pod_manager


def get_pod_manager():
    global __pod_manager

    with pod_manager_lock:
        return __pod_manager


def is_primary_allocator_grpc(config_manager) -> bool:
    from titus_isolate.isolate.utils import get_allocator
    from titus_isolate.allocate.remote.allocator import GrpcRemoteIsolationAllocator
    primary_alloc_str = config_manager.get_cached_str(CPU_ALLOCATOR)
    primary_allocator = get_allocator(primary_alloc_str, config_manager)
    return primary_allocator.get_name() == GrpcRemoteIsolationAllocator.__name__        


def get_cell_name():
    config_manager = get_config_manager()
    if config_manager is None:
        log.warning("Config manager is not yet set.")
        return UNKNOWN_CELL

    if not is_primary_allocator_grpc(config_manager):
        log.info("Fetching cell for an http allocator")
        fetch_fun = get_http_cell_name
    else:
        log.info("Fetching cell for the grpc allocator")
        fetch_fun = get_grpc_cell_name

    try:
        cell_name = fetch_fun(config_manager)
        log.info("Cell: %s", cell_name)
        return cell_name
    except Exception:
        log.error("Failed to determine isolation cell.")
        return UNKNOWN_CELL 


def get_http_cell_name(config_manager):
    url = config_manager.get_cached_str(REMOTE_ALLOCATOR_URL)
    if url is None:
        log.warning("No remote solver URL specified.")
        return UNKNOWN_CELL

    timeout = config_manager.get_cached_int(MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME)

    response = requests.get(url, timeout=timeout)
    cell_name = response.headers.get(TITUS_ISOLATE_CELL_HEADER, None)
    if cell_name is None:
        log.warning("Titus isolation cell header is not set.")
        return UNKNOWN_CELL
    return cell_name


def get_grpc_cell_name(config_manager):
    endpoint = config_manager.get_cached_str(GRPC_REMOTE_ALLOC_ENDPOINT, None)
    if endpoint is None:
        log.warning("Could not get grpc remote allocator endpoint address.")
        return UNKNOWN_CELL
    stub = IsolationServiceStub(grpc.insecure_channel(endpoint))
    res = stub.GetCurrentCell(CurrentCellRequest(), timeout=5.0)
    if res.cell_id == "":
        log.warning("Service returned empty grpc cell header")
        return UNKNOWN_CELL
    return res.cell_id


def is_kubernetes() -> bool:
    return get_config_manager().get_cached_bool(KUBERNETES_BACKEND_KEY, True)


def start_periodic_scheduling(exit_handler: ExitHandler):
    global scheduling_started

    with scheduling_lock:
        if scheduling_started:
            return

        worker_thread = Thread(target=__schedule_loop, args=[exit_handler])
        worker_thread.daemon = True
        worker_thread.start()
        scheduling_started = True


def is_running_on_agent():
    return 'NOTIFY_SOCKET' in os.environ and 'TITUS_TASK_ID' not in os.environ


def _notify_watchdog():
    if is_running_on_agent():
        from systemd import daemon
        from systemd.daemon import Notification
        daemon.notify(Notification.WATCHDOG)


def __schedule_loop(exit_handler: ExitHandler):
    log.info("Starting scheduling loop...")
    while True:
        try:
            sleep_time = _schedule_once(exit_handler)
            _notify_watchdog()
            log.debug("Scheduling thread sleeping for: '%d' seconds", sleep_time)
            time.sleep(sleep_time)
        except Exception:
            log.error("Failed to run scheduling loop")
            exit_handler.exit(SCHEDULING_LOOP_FAILURE_EXIT_CODE)


def _schedule_once(exit_handler: ExitHandler) -> float:
    try:
        log.debug("Running pending scheduled tasks.")
        schedule.run_pending()

        sleep_time = SCHEDULING_SLEEP_INTERVAL
        if schedule.next_run() is not None:
            sleep_time = schedule.idle_seconds()

        if sleep_time < 0:
            sleep_time = SCHEDULING_SLEEP_INTERVAL

        return sleep_time
    except Exception:
        log.error("Failed to run scheduling once")
        exit_handler.exit(SCHEDULE_ONCE_FAILURE_EXIT_CODE)
