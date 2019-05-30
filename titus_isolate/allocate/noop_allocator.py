from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator


class NoopCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider=None):
        pass

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        log.info("Ignoring attempt to assign threads to workload: '{}'".format(request.get_workload_id()))
        return AllocateResponse(request.get_cpu(), self.get_name())

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        log.info("Ignoring attempt to free threads for workload: '{}'".format(request.get_workload_id()))
        return AllocateResponse(request.get_cpu(), self.get_name())

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        log.info("Ignoring attempt to rebalance workloads: '{}'".format(request.get_workloads()))
        return AllocateResponse(request.get_cpu(), self.get_name())

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
