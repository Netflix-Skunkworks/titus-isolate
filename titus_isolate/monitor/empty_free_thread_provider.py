from typing import Dict, List

from titus_isolate import log
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class EmptyFreeThreadProvider(FreeThreadProvider):

    def get_free_threads(
            self,
            cpu: Cpu,
            workload_map: Dict[str, Workload],
            cpu_usage: Dict[str, float] = None) -> List[Thread]:
        return [t for t in cpu.get_threads() if len(t.get_workload_ids()) == 0]
