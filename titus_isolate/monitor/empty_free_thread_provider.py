from typing import Dict, List

from titus_isolate.metrics.constants import FREE_THREADS_KEY
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class EmptyFreeThreadProvider(FreeThreadProvider):

    def __init__(self):
        self.__reg = None
        self.__last_free_thread_count = 0

    def get_free_threads(
            self,
            cpu: Cpu,
            workload_map: Dict[str, Workload],
            cpu_usage: Dict[str, float] = None) -> List[Thread]:

        free_threads = [t for t in cpu.get_threads() if len(t.get_workload_ids()) == 0]
        self.__last_free_thread_count = len(free_threads)
        return free_threads

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(FREE_THREADS_KEY, tags).set(self.__last_free_thread_count)

