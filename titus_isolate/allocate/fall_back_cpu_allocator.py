from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.metrics.constants import FALLBACK_ALLOCATOR_COUNT, FALLBACK_ASSIGN_COUNT, FALLBACK_FREE_COUNT, \
    FALLBACK_REBALANCE_COUNT
from titus_isolate.model.processor.cpu import Cpu


class FallbackCpuAllocator(CpuAllocator):

    def __init__(self, primary_cpu_allocator, secondary_cpu_allocator):
        if primary_cpu_allocator is None:
            raise ValueError("Must be provided a primary cpu allocator.")

        if secondary_cpu_allocator is None:
            raise ValueError("Must be provided a secondary cpu allocator.")

        self.__reg = None

        self.__primary_allocator = primary_cpu_allocator
        self.__secondary_allocator = secondary_cpu_allocator

        self.__secondary_assign_threads_call_count = 0
        self.__secondary_free_threads_call_count = 0
        self.__secondary_rebalance_call_count = 0

        log.debug(
            "Created FallbackCpuAllocator with primary cpu allocator: '{}' and secondary cpu allocator: '{}'".format(
                self.__primary_allocator.__class__.__name__,
                self.__secondary_allocator.__class__.__name__))

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        try:
            return self.__primary_allocator.assign_threads(cpu, workload_id, workloads)
        except:
            log.exception(
                "Failed to assign threads to workload: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    workload_id,
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            self.__secondary_assign_threads_call_count += 1
            cpu = self.__secondary_allocator.assign_threads(cpu, workload_id, workloads)
            return cpu

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        try:
            return self.__primary_allocator.free_threads(cpu, workload_id, workloads)
        except:
            log.exception(
                "Failed to free threads for workload: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    workload_id,
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            self.__secondary_free_threads_call_count += 1
            cpu = self.__secondary_allocator.free_threads(cpu, workload_id, workloads)
            return cpu

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        try:
            return self.__primary_allocator.rebalance(cpu, workloads)
        except:
            log.exception(
                "Failed to rebalance workloads: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    workloads,
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            self.__secondary_rebalance_call_count += 1
            cpu = self.__secondary_allocator.rebalance(cpu, workloads)
            return cpu

    def get_primary_allocator(self) -> CpuAllocator:
        return self.__primary_allocator

    def get_secondary_allocator(self) -> CpuAllocator:
        return self.__secondary_allocator

    def get_fallback_allocator_calls_count(self):
        return self.__secondary_assign_threads_call_count + \
               self.__secondary_free_threads_call_count + \
               self.__secondary_rebalance_call_count

    def set_registry(self, registry):
        self.__reg = registry
        self.__primary_allocator.set_registry(registry)
        self.__secondary_allocator.set_registry(registry)

    def report_metrics(self, tags):
        self.__reg.gauge(FALLBACK_ALLOCATOR_COUNT, tags).set(self.get_fallback_allocator_calls_count())
        self.__reg.gauge(FALLBACK_ASSIGN_COUNT, tags).set(self.__secondary_assign_threads_call_count)
        self.__reg.gauge(FALLBACK_FREE_COUNT, tags).set(self.__secondary_free_threads_call_count)
        self.__reg.gauge(FALLBACK_REBALANCE_COUNT, tags).set(self.__secondary_rebalance_call_count)
        self.__primary_allocator.report_metrics(tags)
        self.__secondary_allocator.report_metrics(tags)

    def str(self):
        return "FallbackCpuAllocator(primary: {}, secondary: {})".format(
            self.__primary_allocator.__class__.__name__,
            self.__secondary_allocator.__class__.__name__)
