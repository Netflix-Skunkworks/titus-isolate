from titus_isolate import log

NUMA_BALANCING_PATH = '/proc/sys/kernel/numa_balancing'


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