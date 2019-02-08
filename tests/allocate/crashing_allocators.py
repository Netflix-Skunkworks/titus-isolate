from titus_isolate.allocate.cpu_allocator import CpuAllocator


class CrashingAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload):
        raise Exception("")

    def free_threads(self, cpu, workload_id):
        raise Exception("")


class CrashingAssignAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload):
        raise Exception("")

    def free_threads(self, cpu, workload_id):
        pass