from typing import List, Dict

from titus_isolate import log
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class ThresholdFreeThreadProvider(FreeThreadProvider):

    def __init__(self, total_threshold: float):
        """
        This class determines whether threads are free based on the cpu usage of workloads.

        :param total_threshold: The percentage of usage under which threads are considered to be free.
        """
        self.__total_threshold = total_threshold
        log.debug("ThresholdFreeThreadProvider created with threshold: '{}'".format(self.__total_threshold))

    def get_free_threads(
            self,
            cpu: Cpu,
            workload_map: Dict[str, Workload],
            cpu_usage: Dict[str, float] = None) -> List[Thread]:

        if cpu_usage is None:
            log.error("CPU usage is required, defaulting to EMPTY threads being free.")
            return cpu.get_empty_threads()

        free_threads = []
        for package in cpu.get_packages():
            for core in package.get_cores():
                free_threads += self.__get_free_threads(package, core, cpu_usage, workload_map)

        return free_threads

    def __get_free_threads(
            self,
            package: Package,
            core: Core,
            workload_usage: Dict[str, float],
            workload_map: Dict[str, Workload]):

        # At this point the core is partially allocated (one thread allocated, one thread unallocated).
        # If the sum of STATIC predicted CPU usage exceeds the threshold no threads are free to be allocated.
        workload_ids = []
        for t in core.get_threads():
            workload_ids += t.get_workload_ids()

        predicted_static_usage = 0
        static_workload_ids = []
        for w_id in workload_ids:
            workload = workload_map.get(w_id, None)
            if workload is not None and workload.get_type() == STATIC:
                predicted_static_usage += \
                    workload_usage.get(w_id, workload.get_thread_count()) / workload.get_thread_count()
                static_workload_ids.append(w_id)

        is_free = predicted_static_usage <= self.__total_threshold

        log.info(
            "Package:Core {}:{} is free: {} based on predicted static usage: {} threshold: {} for workloads: {}".format(
                package.get_id(),
                core.get_id(),
                is_free,
                predicted_static_usage,
                self.__total_threshold,
                static_workload_ids))

        if is_free:
            return core.get_empty_threads()
        else:
            return []

