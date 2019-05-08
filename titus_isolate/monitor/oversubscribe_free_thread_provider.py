from typing import Dict, List

from titus_isolate import log
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider
from titus_isolate.monitor.utils import get_free_cores


class OversubscribeFreeThreadProvider(FreeThreadProvider):
    def __init__(self, total_threshold: float):
        """
        This class determines whether threads are free based on the cpu usage of workloads.

        :param total_threshold: The percentage of usage under which threads are considered to be free.
        """
        self.__threshold = total_threshold
        log.debug("{} created with threshold: '{}'".format(self.__class__.__name__, self.__threshold))

    def get_free_threads(
            self,
            cpu: Cpu,
            workload_map:
            Dict[str, Workload],
            cpu_usage: Dict[str, float] = None) -> List[Thread]:

        if cpu_usage is None:
            log.error("CPU usage is required, defaulting to EMPTY threads being free.")
            return cpu.get_empty_threads()

        free_threads = []
        for c in get_free_cores(self.__threshold, cpu, workload_map, cpu_usage):
            free_threads += c.get_threads()

        return free_threads
