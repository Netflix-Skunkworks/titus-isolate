from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.utils import get_burst_workloads, release_threads
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread


def _is_thread_available(thread: Thread, workloads: dict):
    if not thread.is_claimed():
        return True

    for w_id in thread.get_workload_ids():
        if workloads[w_id].get_type() == STATIC:
            return False

    return True


class BurstCpuAllocator(CpuAllocator):

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        burst_workloads = [w for w in get_burst_workloads(workloads.values())]
        return self.__reset_burst_assignments(cpu, burst_workloads, workloads)

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        release_threads(cpu, workload_id)
        burst_workloads = [w for w in get_burst_workloads(workloads.values()) if w.get_id() != workload_id]
        return self.__reset_burst_assignments(cpu, burst_workloads, workloads)

    def __reset_burst_assignments(self, cpu: Cpu, burst_workloads: list, workloads: dict):
        for w in burst_workloads:
            release_threads(cpu, w.get_id())

        for w in burst_workloads:
            self.__assign_threads(cpu, w.get_id(), workloads)

        return cpu

    @staticmethod
    def __assign_threads(cpu: Cpu, workload_id: str, workloads: dict):
        for t in cpu.get_threads():
            if _is_thread_available(t, workloads):
                t.claim(workload_id)

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass

