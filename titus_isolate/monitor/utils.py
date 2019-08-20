from typing import Dict, List

from titus_isolate import log
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload


def get_free_cores(
        threshold: float,
        cpu: Cpu,
        workload_map: Dict[str, Workload],
        cpu_usage: Dict[str, float]) -> List[Core]:

    return [c for c in cpu.get_cores() if is_core_below_threshold(threshold, c, cpu_usage, workload_map)]


def is_core_below_threshold(
        threshold: float,
        core: Core,
        workload_usage: Dict[str, float],
        workload_map: Dict[str, Workload]):

    # Get all workload IDs running on this core
    workload_ids = []
    for t in core.get_threads():
        workload_ids += t.get_workload_ids()

    # Measure the usage of all _static_ workloads running on this core in proportion to their requested thread count.
    #
    # e.g.
    # w_id  | usage
    #    a  |    2%
    #    b  |    3%
    #    c  |    1%
    # -------------
    # total |    6%
    usage = 0
    for w_id in workload_ids:
        workload = workload_map.get(w_id, None)
        if workload is not None and workload.get_type() == STATIC:
            usage += workload_usage.get(w_id, workload.get_thread_count()) / workload.get_thread_count()

    # If we set the threshold to 10% and continue the example above
    #
    # e.g.
    # is_free = 6% <= 10%
    # is_free = true
    is_free = usage <= threshold

    if is_free:
        log.debug("Core: {} with usage: {} is UNDER threshold: {}".format(core.get_id(), usage, threshold))
    else:
        log.debug("Core: {} with usage: {} is OVER  threshold: {}".format(core.get_id(), usage, threshold))

    return is_free
