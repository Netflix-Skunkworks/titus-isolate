from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.cgroup.file_cgroup_manager import FileCgroupManager


class NoopResetCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider=None, cgroup_manager=FileCgroupManager()):
        self.__cgroup_manager = cgroup_manager

    def get_cgroup_manager(self):
        return self.__cgroup_manager

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        thread_count = len(request.get_cpu().get_threads())
        thread_ids = list(range(thread_count))

        log.info("Setting cpuset.cpus to ALL cpus: '{}' for workload: '{}'".format(thread_ids, request.get_workload_id()))
        self.__cgroup_manager.set_cpuset(request.get_workload_id(), thread_ids)

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
