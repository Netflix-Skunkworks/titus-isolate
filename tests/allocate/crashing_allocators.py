from titus_isolate.allocate.cpu_allocator import CpuAllocator


class CrashingAllocator(CpuAllocator):

    def __init__(self, cpu):
        self.__cpu = cpu

    def get_cpu(self):
        return self.__cpu

    def assign_threads(self, workload):
        raise Exception("")

    def free_threads(self, workload_id):
        raise Exception("")


class CrashingAssignAllocator(CpuAllocator):

    def __init__(self, cpu):
        self.__cpu = cpu

    def get_cpu(self):
        return self.__cpu

    def assign_threads(self, workload):
        raise Exception("")

    def free_threads(self, workload_id):
        pass