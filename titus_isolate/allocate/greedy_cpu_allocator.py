from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse, get_workload_allocations
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.legacy_workload import LegacyWorkload
from titus_isolate.model.processor.utils import get_emptiest_core, is_cpu_full


class GreedyCpuAllocator(CpuAllocator):

    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        cpu.clear()

        for task_id, workload in request.get_workloads().items():
            self.__assign_threads(cpu, workload)

        return AllocateResponse(
            cpu,
            get_workload_allocations(cpu, list(request.get_workloads().values())),
            self.get_name(),
            {})

    def get_name(self) -> str:
        return self.__class__.__name__

    def __assign_threads(self, cpu, workload):
        thread_count = workload.get_thread_count()
        claimed_threads = []

        if thread_count == 0:
            return claimed_threads

        if is_cpu_full(cpu):
            raise ValueError("Failed to add workload: '{}', cpu is full: {}".format(workload.get_task_id(), cpu))

        package = cpu.get_emptiest_package()

        while thread_count > 0 and len(package.get_empty_threads()) > 0:
            core = get_emptiest_core(package)
            empty_threads = core.get_empty_threads()[:thread_count]

            for empty_thread in empty_threads:
                log.debug("Claiming package:core:thread '{}:{}:{}' for workload '{}'".format(
                    package.get_id(), core.get_id(), empty_thread.get_id(), workload.get_task_id()))
                empty_thread.claim(workload.get_task_id())
                claimed_threads.append(empty_thread)
                thread_count -= 1

        return claimed_threads + self.__assign_threads(
            cpu,
            LegacyWorkload(
                task_id=workload.get_task_id(),
                job_id=workload.get_job_id(),
                thread_count=thread_count))

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
