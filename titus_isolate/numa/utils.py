from titus_isolate import log
from titus_isolate.config.constants import TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING, \
    DEFAULT_TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_config_manager

NUMA_BALANCING_PATH = '/proc/sys/kernel/numa_balancing'


def update_numa_balancing(workload: Workload, cpu: Cpu):
    try:
        config_manager = get_config_manager()
        dynamic_numa_balancing_enabled = config_manager.get_bool(
            TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING,
            DEFAULT_TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING)

        if not dynamic_numa_balancing_enabled:
            enable_numa_balancing()
            return

        if _occupies_entire_cpu(workload, cpu):
            disable_numa_balancing()
        else:
            enable_numa_balancing()
    except:
        log.error("Failed to update NUMA balancing.")


def enable_numa_balancing():
    if _get_numa_balancing() == 1:
        log.info("NUMA balancing is enabled.")
        return

    log.info("Enabling NUMA balancing.")
    _set_numa_balancing(1)


def disable_numa_balancing():
    if _get_numa_balancing() == 0:
        log.info("NUMA balancing is disabled.")
        return

    log.info("Disabling NUMA balancing")
    _set_numa_balancing(0)


def _get_numa_balancing():
    with open(NUMA_BALANCING_PATH, 'r') as f:
        return int(f.read())


def _set_numa_balancing(state: int):
    if state != 0 and state != 1:
        raise ValueError("numa_balancing may be set to either 0 or 1, received: '{}'".format(state))

    with open(NUMA_BALANCING_PATH, 'w') as f:
        f.write(str(state))


def _occupies_entire_cpu(workload: Workload, cpu: Cpu):
    return len(cpu.get_threads()) == workload.get_thread_count()
