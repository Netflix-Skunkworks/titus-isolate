from titus_isolate.allocate.cpu_allocator import CpuAllocator


class CrashingAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload_id, workloads):
        raise Exception("")

    def free_threads(self, cpu, workload_id, workloads):
        raise Exception("")

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass


class CrashingAssignAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload_id, workloads):
        raise Exception("")

    def free_threads(self, cpu, workload_id, workloads):
        pass

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
