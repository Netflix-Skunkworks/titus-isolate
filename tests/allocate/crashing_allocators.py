from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.cpu_allocator import CpuAllocator


class CrashingAllocator(CpuAllocator):

    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        raise Exception("crashing on purpose")

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
