from functools import reduce
from typing import Dict, List

from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class EmptyCoreFreeThreadProvider(FreeThreadProvider):

    def get_free_threads(
            self,
            cpu: Cpu,
            workload_map: Dict[str, Workload],
            cpu_usage: Dict[str, float] = None) -> List[Thread]:
        free_cores = [c.get_threads() for c in cpu.get_cores() if len(c.get_empty_threads()) == 2]
        if len(free_cores) == 0:
            return []

        return reduce(list.__add__, free_cores)
