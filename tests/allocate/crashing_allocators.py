from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu


class CrashingAllocator(CpuAllocator):

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        raise Exception("")

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        raise Exception("")

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        raise Exception("")

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass


class CrashingAssignAllocator(CpuAllocator):

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        raise Exception("")

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        pass

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        pass

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
