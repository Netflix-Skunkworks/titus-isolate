from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse, get_workload_allocations
from titus_isolate.allocate.cpu_allocator import CpuAllocator


class NoopCpuAllocator(CpuAllocator):

    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        log.info("Ignoring attempt isolate")
        return AllocateResponse(
            request.get_cpu(),
            get_workload_allocations(request.get_cpu(), list(request.get_workloads().values())),
            self.get_name())

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
