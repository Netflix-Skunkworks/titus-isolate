from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator


class NoopCpuAllocator(CpuAllocator):

    def __init__(self, cpu):
        self.__cpu = cpu

    def get_cpu(self):
        return self.__cpu

    def assign_threads(self, workload):
        log.info("Ignoring attempt to assign threads to workload: '{}'".format(workload))

    def free_threads(self, workload_id):
        log.info("Ignoring attempt to free threads for workload: '{}'".format(workload_id))
