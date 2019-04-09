from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu


class CrashingAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload_id, workloads):
        raise Exception("")

    def free_threads(self, cpu, workload_id, workloads):
        raise Exception("")

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        raise Exception("")

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass


class CrashingAssignAllocator(CpuAllocator):

    def assign_threads(self, cpu, workload_id, workloads):
        raise Exception("")

    def free_threads(self, cpu, workload_id, workloads):
        pass

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        pass

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
