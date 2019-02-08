from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.utils import get_emptiest_core
from titus_isolate.model.workload import Workload


class GreedyCpuAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload):
        self.__assign_threads(cpu, workload)
        return cpu

    def __assign_threads(self, cpu, workload):
        thread_count = workload.get_thread_count()
        claimed_threads = []

        if thread_count == 0:
            return claimed_threads

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
            Workload(workload.get_id(), thread_count, workload.get_type()))

    def free_threads(self, cpu, workload_id):
        for t in cpu.get_threads():
            if t.get_workload_id() == workload_id:
                t.free()

        return cpu

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass

