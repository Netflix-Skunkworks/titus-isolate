from typing import List

from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse, get_workload_allocations
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload_interface import Workload


class NoopResetCpuAllocator(CpuAllocator):

    def __init__(self):
        pass

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        log.info("Assigning all threads to workload: '{}'".format(request.get_workload_id()))
        return self.rebalance(request)

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        log.info("Freeing all threads of workload: '{}'".format(request.get_workload_id()))
        cpu = self.__assign_all_to_all(request.get_cpu(), list(request.get_workloads().values()))
        for t in request.get_cpu().get_threads():
            t.free(request.get_workload_id())

        return AllocateResponse(
            cpu,
            get_workload_allocations(cpu, list(request.get_workloads().values())),
            self.get_name())

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        log.info("Assigning all threads to all workloads on request to rebalance workloads: '{}'".format(request.get_workloads()))
        cpu = self.__assign_all_to_all(request.get_cpu(), list(request.get_workloads().values()))

        return AllocateResponse(
            cpu,
            get_workload_allocations(cpu, list(request.get_workloads().values())),
            self.get_name())

    def __assign_all_to_all(self, cpu: Cpu, workloads: List[Workload]) -> Cpu:
        for t in cpu.get_threads():
            t.clear()

        for w in workloads:
            for t in cpu.get_threads():
                t.claim(w.get_id())

        return cpu

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass

