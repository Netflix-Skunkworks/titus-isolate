from titus_isolate import log
from titus_isolate.allocate.fall_back_cpu_allocator import FallbackCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.remote.allocator import GrpcRemoteIsolationAllocator
from titus_isolate.config.constants import CPU_ALLOCATOR, CPU_ALLOCATORS, DEFAULT_ALLOCATOR,  GREEDY, NOOP, \
    GRPC_REMOTE, FALLBACK_ALLOCATOR, DEFAULT_FALLBACK_ALLOCATOR, NAIVE, RESOURCE_USAGE_PROVIDER, \
    DEFAULT_RESOURCE_USAGE_PROVIDER, PROMETHEUS
from titus_isolate.monitor.noop_resource_usage_provider import NoopResourceUsageProvider
from titus_isolate.monitor.prom_resource_usage_provider import PrometheusResourceUsageProvider

CPU_ALLOCATOR_NAME_TO_CLASS_MAP = {
    GREEDY: GreedyCpuAllocator,
    NAIVE: NaiveCpuAllocator,
    NOOP: NoopCpuAllocator,
    GRPC_REMOTE: GrpcRemoteIsolationAllocator
}


def get_fallback_allocator(config_manager) -> FallbackCpuAllocator:
    primary_alloc_str = config_manager.get_str(CPU_ALLOCATOR)
    secondary_alloc_str = config_manager.get_str(FALLBACK_ALLOCATOR, DEFAULT_FALLBACK_ALLOCATOR)

    primary_allocator = get_allocator(primary_alloc_str)
    secondary_allocator = get_allocator(secondary_alloc_str)

    return FallbackCpuAllocator(primary_allocator, secondary_allocator)


def get_allocator(allocator_str):
    if allocator_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(allocator_str, DEFAULT_ALLOCATOR))
        allocator_str = DEFAULT_ALLOCATOR

    return CPU_ALLOCATOR_NAME_TO_CLASS_MAP[allocator_str]()


def get_resource_usage_provider(config_manager):
    rup_str = config_manager.get_cached_str(RESOURCE_USAGE_PROVIDER, DEFAULT_RESOURCE_USAGE_PROVIDER)

    log.info("ResourceUsageProvider: %s", rup_str)

    if rup_str == PROMETHEUS:
        return PrometheusResourceUsageProvider()

    if rup_str == NOOP:
        return NoopResourceUsageProvider()
