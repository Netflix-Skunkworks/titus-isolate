import time
from threading import Thread, Lock

import schedule

from titus_isolate import log
from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.config_manager import ConfigManager

SCHEDULING_SLEEP_INTERVAL = 1.0

scheduling_lock = Lock()
scheduling_started = False

config_manager_lock = Lock()
__config_manager = None

workload_manager_lock = Lock()
__workload_manager = None

event_manager_lock = Lock()
__event_manager = None

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
