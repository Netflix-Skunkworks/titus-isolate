from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator


class NoopCpuAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload):
        log.info("Ignoring attempt to assign threads to workload: '{}'".format(workload.get_id()))

    def free_threads(self, cpu, workload_id):
        log.info("Ignoring attempt to free threads for workload: '{}'".format(workload_id))

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
