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

    workload_ids = []
    for t in core.get_threads():
        workload_ids += t.get_workload_ids()

    static_usage = 0
    static_workload_ids = []
    for w_id in workload_ids:
        workload = workload_map.get(w_id, None)
        if workload is not None and workload.get_type() == STATIC:
            static_usage += \
                workload_usage.get(w_id, workload.get_thread_count()) / workload.get_thread_count()
            static_workload_ids.append(w_id)

    is_free = static_usage <= threshold

    if is_free:
        log.info("Core: {} with usage: {} is UNDER threshold: {}".format(core.get_id(), static_usage, threshold))
    else:
        log.info("Core: {} with usage: {} is OVER  threshold: {}".format(core.get_id(), static_usage, threshold))

    return is_free
