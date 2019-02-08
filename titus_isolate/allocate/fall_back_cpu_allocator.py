from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.metrics.constants import FALLBACK_ALLOCATOR_COUNT


class FallbackCpuAllocator(CpuAllocator):

    def __init__(self, primary_cpu_allocator, secondary_cpu_allocator):
        if primary_cpu_allocator is None:
            raise ValueError("Must be provided a primary cpu allocator.")

        if secondary_cpu_allocator is None:
            raise ValueError("Must be provided a secondary cpu allocator.")

        self.__reg = None

        self.__primary_allocator = primary_cpu_allocator
        self.__secondary_allocator = secondary_cpu_allocator

        self.__primary_allocator_calls_count = 0
        self.__secondary_allocator_calls_count = 0

        log.info("Created FallbackCpuAllocator with primary cpu allocator: '{}' and secondary cpu allocator: '{}'".format(
            self.__primary_allocator.__class__.__name__,
            self.__secondary_allocator.__class__.__name__))

    def assign_threads(self, cpu, workload):
        try:
            cpu = self.__primary_allocator.assign_threads(cpu, workload)
            self.__primary_allocator_calls_count += 1
            return cpu
        except:
            log.exception(
                "Failed to assign threads to workload: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    workload.get_id(),
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            cpu = self.__secondary_allocator.assign_threads(cpu, workload)
            self.__secondary_allocator_calls_count += 1
            return cpu

    def free_threads(self, cpu, workload_id):
        try:
            cpu = self.__primary_allocator.free_threads(cpu, workload_id)
            self.__primary_allocator_calls_count += 1
            return cpu
        except:
            log.exception(
                "Failed to free threads for workload: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    workload_id,
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            cpu = self.__secondary_allocator.free_threads(cpu, workload_id)
            self.__secondary_allocator_calls_count += 1
            return cpu

    def get_fallback_allocator_calls_count(self):
        return self.__secondary_allocator_calls_count

    def set_registry(self, registry):
        self.__reg = registry
        self.__primary_allocator.set_registry(registry)
        self.__secondary_allocator.set_registry(registry)

    def report_metrics(self, tags):
        self.__reg.gauge(FALLBACK_ALLOCATOR_COUNT, tags).set(self.get_fallback_allocator_calls_count())
        self.__primary_allocator.report_metrics(tags)
        self.__secondary_allocator.report_metrics(tags)

    def str(self):
        return "FallbackCpuAllocator(primary: {}, secondary: {})".format(
            self.__primary_allocator.__class__.__name__,
            self.__secondary_allocator.__class__.__name__)
