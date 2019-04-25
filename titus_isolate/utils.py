import time
from threading import Thread, Lock

import requests
import schedule

from titus_isolate import log
from titus_isolate.allocate.constants import TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL
from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import REMOTE_ALLOCATOR_URL

SCHEDULING_SLEEP_INTERVAL = 1.0

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


def get_cell_name():
    config_manager = get_config_manager()
    if config_manager is None:
        log.warning("Config manager is not yet set.")
        return UNKNOWN_CELL

    url = config_manager.get_str(REMOTE_ALLOCATOR_URL)
    if url is None:
        log.warning("No remote solver URL specified.")
        return UNKNOWN_CELL

    try:
        response = requests.get(url, timeout=1)
        cell_name = response.headers.get(TITUS_ISOLATE_CELL_HEADER, None)
        if cell_name is None:
            log.warning("Titus isolation cell header is not set.")
            return UNKNOWN_CELL
        else:
            return cell_name
    except:
        log.exception("Failed to determine isolation cell.")
        return UNKNOWN_CELL


def start_periodic_scheduling():
    global scheduling_started

    with scheduling_lock:
        if scheduling_started:
            return

        worker_thread = Thread(target=__schedule_loop)
        worker_thread.daemon = True
        worker_thread.start()
        scheduling_started = True


def __schedule_loop():
    while True:
        log.debug("Running pending scheduled tasks.")
        schedule.run_pending()

        sleep_time = SCHEDULING_SLEEP_INTERVAL
        if schedule.next_run() is not None:
            sleep_time = schedule.idle_seconds()

        if sleep_time < 0:
            sleep_time = SCHEDULING_SLEEP_INTERVAL

        log.debug("Scheduling thread sleeping for: '{}' seconds".format(sleep_time))
        time.sleep(sleep_time)
