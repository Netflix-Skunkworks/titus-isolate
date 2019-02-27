from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class EmptyFreeThreadProvider(FreeThreadProvider):

    def get_free_threads(self, cpu: Cpu) -> list:
        return [t for t in cpu.get_threads() if len(t.get_workload_ids()) == 0]
