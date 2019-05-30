from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.utils import get_emptiest_core, is_cpu_full
from titus_isolate.model.utils import get_burst_workloads, release_all_threads, update_burst_workloads, rebalance
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.empty_free_thread_provider import EmptyFreeThreadProvider
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


class GreedyCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider: FreeThreadProvider = EmptyFreeThreadProvider()):
        self.__free_thread_provider = free_thread_provider

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workloads = request.get_workloads()
        workload_id = request.get_workload_id()

        burst_workloads = get_burst_workloads(workloads.values())
        release_all_threads(cpu, burst_workloads)
        if workloads[workload_id].get_type() == STATIC:
            self.__assign_threads(cpu, workloads[workload_id])
        update_burst_workloads(cpu, workloads, self.__free_thread_provider)

        return AllocateResponse(cpu, self.get_name())

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workloads = request.get_workloads()
        workload_id = request.get_workload_id()

        burst_workloads = get_burst_workloads(workloads.values())
        release_all_threads(cpu, burst_workloads)
        for t in cpu.get_threads():
            if workload_id in t.get_workload_ids():
                t.free(workload_id)

        workloads.pop(workload_id)
        update_burst_workloads(cpu, workloads, self.__free_thread_provider)

        return AllocateResponse(cpu, self.get_name())

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workloads = request.get_workloads()

        cpu = rebalance(cpu, workloads, self.__free_thread_provider)
        return AllocateResponse(cpu, self.get_name())

    def get_name(self) -> str:
        return self.__class__.__name__

    def __assign_threads(self, cpu, workload):
        thread_count = workload.get_thread_count()
        claimed_threads = []

        if thread_count == 0:
            return claimed_threads

        if is_cpu_full(cpu):
            raise ValueError("Failed to add workload: '{}', cpu is full: {}".format(workload.get_id(), cpu))

        package = cpu.get_emptiest_package()

        while thread_count > 0 and len(package.get_empty_threads()) > 0:
            core = get_emptiest_core(package)
            empty_threads = core.get_empty_threads()[:thread_count]

            for empty_thread in empty_threads:
                log.debug("Claiming package:core:thread '{}:{}:{}' for workload '{}'".format(
                    package.get_id(), core.get_id(), empty_thread.get_id(), workload.get_id()))
                empty_thread.claim(workload.get_id())
                claimed_threads.append(empty_thread)
                thread_count -= 1

        return claimed_threads + self.__assign_threads(
            cpu,
            Workload(
                identifier=workload.get_id(),
                thread_count=thread_count,
                mem=workload.get_mem(),
                disk=workload.get_disk(),
                network=workload.get_network(),
                app_name=workload.get_app_name(),
                owner_email=workload.get_owner_email(),
                image=workload.get_image(),
                command=workload.get_command(),
                entrypoint=workload.get_entrypoint(),
                job_type=workload.get_job_type(),
                workload_type=workload.get_type()))

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
