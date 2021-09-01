from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.config.constants import FALLBACK_QUEUE_DEPTH, DEFAULT_FALLBACK_QUEUE_DEPTH
from titus_isolate.metrics.constants import FALLBACK_ASSIGN_COUNT, FALLBACK_FREE_COUNT, \
    FALLBACK_REBALANCE_COUNT, PRIMARY_ASSIGN_COUNT, PRIMARY_FREE_COUNT, PRIMARY_REBALANCE_COUNT, \
    FALLBACK_QUEUE_DEPTH_COUNT
from titus_isolate.utils import get_event_manager, get_config_manager


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

        self.__queue_depth_fallback_count = 0

        cm = get_config_manager()
        self.__fallback_queue_depth = cm.get_cached_int(FALLBACK_QUEUE_DEPTH, DEFAULT_FALLBACK_QUEUE_DEPTH)

        log.info(
            "Created FallbackCpuAllocator with primary cpu allocator: '{}' and secondary cpu allocator: '{}', fallback queue depth: '{}'".format(
                self.__primary_allocator.__class__.__name__,
                self.__secondary_allocator.__class__.__name__,
                self.__fallback_queue_depth))

    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        try:
            self.__primary_assign_threads_call_count += 1
            self.__should_fallback_immediately()
            return self.__primary_allocator.isolate(request)
        except Exception as e:
            log.error(
                "Failed to isolate with primary allocator: '%s', falling back to: '%s' because '%s'",
                self.__primary_allocator.__class__.__name__,
                self.__secondary_allocator.__class__.__name__,
                e)
            self.__secondary_assign_threads_call_count += 1
            return self.__secondary_allocator.isolate(request)
        pass

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

    def set_registry(self, registry, tags):
        self.__reg = registry
        self.__primary_allocator.set_registry(registry, tags)
        self.__secondary_allocator.set_registry(registry, tags)

    def report_metrics(self, tags):
        self.__reg.counter(PRIMARY_ASSIGN_COUNT, tags).increment(self.__primary_assign_threads_call_count)
        self.__reg.counter(PRIMARY_FREE_COUNT, tags).increment(self.__primary_free_threads_call_count)
        self.__reg.counter(PRIMARY_REBALANCE_COUNT, tags).increment(self.__primary_rebalance_call_count)
        self.__reg.counter(FALLBACK_ASSIGN_COUNT, tags).increment(self.__secondary_assign_threads_call_count)
        self.__reg.counter(FALLBACK_FREE_COUNT, tags).increment(self.__secondary_free_threads_call_count)
        self.__reg.counter(FALLBACK_REBALANCE_COUNT, tags).increment(self.__secondary_rebalance_call_count)
        self.__reg.counter(FALLBACK_QUEUE_DEPTH_COUNT, tags).increment(self.__queue_depth_fallback_count)

        self.__primary_assign_threads_call_count = 0
        self.__primary_free_threads_call_count = 0
        self.__primary_rebalance_call_count = 0
        self.__secondary_assign_threads_call_count = 0
        self.__secondary_free_threads_call_count = 0
        self.__secondary_rebalance_call_count = 0
        self.__queue_depth_fallback_count = 0

        self.__primary_allocator.report_metrics(tags)
        self.__secondary_allocator.report_metrics(tags)

    def str(self):
        return "FallbackCpuAllocator(primary: {}, secondary: {})".format(
            self.__primary_allocator,
            self.__secondary_allocator)

    def __should_fallback_immediately(self):
        em = get_event_manager()

        if em is not None:
            queue_depth = em.get_queue_depth()
            if queue_depth >= self.__fallback_queue_depth:
                msg = "Falling back due to excessive queue depth: {} > {}".format(
                    queue_depth, self.__fallback_queue_depth)
                log.info(msg)
                self.__queue_depth_fallback_count += 1
                raise Exception(msg)
