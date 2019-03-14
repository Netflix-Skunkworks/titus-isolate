from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu


class NoopCpuAllocator(CpuAllocator):
    def __init__(self, free_thread_provider=""):
        pass

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        log.info("Ignoring attempt to assign threads to workload: '{}'".format(workload_id))

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        log.info("Ignoring attempt to free threads for workload: '{}'".format(workload_id))

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        return cpu

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
