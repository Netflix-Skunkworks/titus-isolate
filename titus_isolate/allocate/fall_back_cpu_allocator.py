from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.metrics.constants import FALLBACK_ASSIGN_COUNT, FALLBACK_FREE_COUNT, \
    FALLBACK_REBALANCE_COUNT, PRIMARY_ASSIGN_COUNT, PRIMARY_FREE_COUNT, PRIMARY_REBALANCE_COUNT


class FallbackCpuAllocator(CpuAllocator):

    def __init__(self, primary_cpu_allocator: CpuAllocator, secondary_cpu_allocator: CpuAllocator):
        if primary_cpu_allocator is None:
            raise ValueError("Must be provided a primary cpu allocator.")

        if secondary_cpu_allocator is None:
            raise ValueError("Must be provided a secondary cpu allocator.")

        self.__reg = None

        self.__primary_allocator = primary_cpu_allocator
        self.__secondary_allocator = secondary_cpu_allocator

        self.__primary_assign_threads_call_count = 0
        self.__primary_free_threads_call_count = 0
        self.__primary_rebalance_call_count = 0

        self.__secondary_assign_threads_call_count = 0
        self.__secondary_free_threads_call_count = 0
        self.__secondary_rebalance_call_count = 0

        log.debug(
            "Created FallbackCpuAllocator with primary cpu allocator: '{}' and secondary cpu allocator: '{}'".format(
                self.__primary_allocator.__class__.__name__,
                self.__secondary_allocator.__class__.__name__))

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        try:
            self.__primary_assign_threads_call_count += 1
            return self.__primary_allocator.assign_threads(request)
        except:
            log.exception(
                "Failed to assign threads to workload: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    request.get_workload_id(),
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            self.__secondary_assign_threads_call_count += 1
            return self.__secondary_allocator.assign_threads(request)

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        try:
            self.__primary_free_threads_call_count += 1
            return self.__primary_allocator.free_threads(request)
        except:
            log.exception(
                "Failed to free threads for workload: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    request.get_workload_id(),
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            self.__secondary_free_threads_call_count += 1
            return self.__secondary_allocator.free_threads(request)

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        try:
            self.__primary_rebalance_call_count += 1
            return self.__primary_allocator.rebalance(request)
        except:
            log.exception(
                "Failed to rebalance workloads: '{}' with primary allocator: '{}', falling back to: '{}'".format(
                    request.get_workloads(),
                    self.__primary_allocator.__class__.__name__,
                    self.__secondary_allocator.__class__.__name__))
            self.__secondary_rebalance_call_count += 1
            return self.__secondary_allocator.rebalance(request)

    def get_name(self) -> str:
        return "{}({},{})".format(
            self.__class__.__name__,
            self.get_primary_allocator().get_name(),
            self.get_secondary_allocator().get_name())

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
        self.__reg.gauge(PRIMARY_ASSIGN_COUNT, tags).set(self.__primary_assign_threads_call_count)
        self.__reg.gauge(PRIMARY_FREE_COUNT, tags).set(self.__primary_free_threads_call_count)
        self.__reg.gauge(PRIMARY_REBALANCE_COUNT, tags).set(self.__primary_rebalance_call_count)
        self.__reg.gauge(FALLBACK_ASSIGN_COUNT, tags).set(self.__secondary_assign_threads_call_count)
        self.__reg.gauge(FALLBACK_FREE_COUNT, tags).set(self.__secondary_free_threads_call_count)
        self.__reg.gauge(FALLBACK_REBALANCE_COUNT, tags).set(self.__secondary_rebalance_call_count)
        self.__primary_allocator.report_metrics(tags)
        self.__secondary_allocator.report_metrics(tags)

    def str(self):
        return "FallbackCpuAllocator(primary: {}, secondary: {})".format(
            self.__primary_allocator,
            self.__secondary_allocator)
