from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu


class CrashingAllocator(CpuAllocator):

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        raise Exception("")

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        raise Exception("")

    def rebalance(self, cpu: Cpu, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        raise Exception("")

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass


class CrashingAssignAllocator(CpuAllocator):

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        raise Exception("")

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        pass

    def rebalance(self, cpu: Cpu, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        pass

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
