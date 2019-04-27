from typing import List, Dict

from titus_isolate import log
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class ThresholdFreeThreadProvider(FreeThreadProvider):

    def __init__(self, total_threshold: float):
        self.__total_threshold = total_threshold
        log.debug("ThresholdFreeThreadProvider created with threshold: '{}'".format(self.__total_threshold))

    def get_free_threads(
            self,
            cpu: Cpu,
            cpu_usage: Dict[str, float],
            workload_map: Dict[str, Workload]) -> List[Thread]:

        log.info("cpu_usage: {}".format(cpu_usage))

        free_threads = []
        for core in cpu.get_cores():
            free_threads += self.__get_free_threads(core, cpu_usage, workload_map)

        return free_threads

    def __get_free_threads(self, core: Core, workload_usage: Dict[str, float], workload_map: Dict[str, Workload]):
        def is_empty(c: Core):
            return len(c.get_empty_threads()) == len(core.get_threads())

        def is_full(c: Core):
            return len(c.get_empty_threads()) == 0

        if is_empty(core):
            return core.get_threads()

        if is_full(core):
            return []

        # At this point the core is partially allocated (one thread allocated, one thread unallocated).
        # If the sum of STATIC predicted CPU usage exceeds the threshold no threads are free to be allocated.
        workload_ids = []
        for t in core.get_threads():
            workload_ids += t.get_workload_ids()

        predicted_static_usage = 0
        for w_id in workload_ids:
            workload = workload_map[w_id]
            if workload.get_type() == STATIC:
                predicted_static_usage += \
                    workload_usage.get(w_id, workload.get_thread_count()) / workload.get_thread_count()

        log.info("Comparing predicted static usage: {} against threshold: {}".format(
            predicted_static_usage, self.__total_threshold))

        if predicted_static_usage > self.__total_threshold:
            return []

        # At this point the empty thread may be allocated to the BURST pool because STATIC workload usage
        # is below the threshold
        return core.get_empty_threads()

