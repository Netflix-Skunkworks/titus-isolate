from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.cgroup.file_cgroup_manager import FileCgroupManager
from titus_isolate.model.processor.cpu import Cpu


class NoopResetCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider="", cgroup_manager=FileCgroupManager()):
        self.__cgroup_manager = cgroup_manager

    def get_cgroup_manager(self):
        return self.__cgroup_manager

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        thread_count = len(cpu.get_threads())
        thread_ids = list(range(thread_count))

        log.info("Setting cpuset.cpus to ALL cpus: '{}' for workload: '{}'".format(thread_ids, workload_id))
        self.__cgroup_manager.set_cpuset(workload_id, thread_ids)

        return cpu

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        log.info("Ignoring attempt to free threads for workload: '{}'".format(workload_id))

    def rebalance(self, cpu: Cpu, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        return cpu

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
