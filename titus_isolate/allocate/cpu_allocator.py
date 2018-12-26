import abc


class CpuAllocator(abc.ABC):

    @abc.abstractmethod
    def get_cpu(self):
        pass

    @abc.abstractmethod
    def assign_threads(self, workload):
        pass

    @abc.abstractmethod
    def free_threads(self, workload_id):
        pass