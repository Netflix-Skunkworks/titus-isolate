from typing import List, Dict

from titus_isolate import log
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class NothingFreeThreadProvider(FreeThreadProvider):

    def get_free_threads(
            self,
            cpu: Cpu,
            cpu_usage: Dict[str, float] = None,
            workload_map: Dict[str, Workload] = None) -> List[Thread]:
        log.info("No threads are free.")
        return []
