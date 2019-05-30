import random
from typing import List

from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.monitor.empty_free_thread_provider import EmptyFreeThreadProvider
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class NaiveCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider: FreeThreadProvider = EmptyFreeThreadProvider()):
        pass

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workload = request.get_workloads()[request.get_workload_id()]
        threads = self._get_assign_threads(cpu, workload.get_thread_count())
        for t in threads:
            t.claim(workload.get_id())

        return AllocateResponse(cpu, self.get_name())

    @staticmethod
    def _get_assign_threads(cpu: Cpu, thread_count: int) -> List[Thread]:
        empty_threads = cpu.get_empty_threads()

        if len(empty_threads) >= thread_count:
            random.shuffle(empty_threads)
            return empty_threads[:thread_count]

        # If there aren't enough empty threads, fill the gap with random claimed threads
        claimed_threads = cpu.get_claimed_threads()
        random.shuffle(claimed_threads)
        claimed_threads = claimed_threads[:thread_count - len(empty_threads)]

        return empty_threads + claimed_threads

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workload = request.get_workloads()[request.get_workload_id()]

        for t in cpu.get_threads():
            t.free(workload.get_id())

        return AllocateResponse(cpu, self.get_name())

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        return AllocateResponse(request.get_cpu(), self.get_name())

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass