
from titus_isolate import log
from titus_isolate.allocate.fall_back_cpu_allocator import FallbackCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.forecast_ip_cpu_allocator import ForecastIPCpuAllocator
from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.allocate.remote_cpu_allocator import RemoteCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, CPU_ALLOCATORS, DEFAULT_ALLOCATOR, \
    IP, GREEDY, NOOP, FORECAST_CPU_IP, \
    NOOP_RESET, FREE_THREAD_PROVIDER, DEFAULT_FREE_THREAD_PROVIDER, EMPTY, THRESHOLD, DEFAULT_TOTAL_THRESHOLD, \
    TOTAL_THRESHOLD, REMOTE, FALLBACK_ALLOCATOR, DEFAULT_FALLBACK_ALLOCATOR, OVERSUBSCRIBE, NAIVE
from titus_isolate.monitor.empty_free_thread_provider import EmptyFreeThreadProvider
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider
from titus_isolate.monitor.oversubscribe_free_thread_provider import OversubscribeFreeThreadProvider
from titus_isolate.monitor.threshold_free_thread_provider import ThresholdFreeThreadProvider
from titus_isolate.utils import get_cpu_usage_predictor_manager

CPU_ALLOCATOR_NAME_TO_CLASS_MAP = {
    IP: IntegerProgramCpuAllocator,
    GREEDY: GreedyCpuAllocator,
    NAIVE: NaiveCpuAllocator,
    NOOP: NoopCpuAllocator,
    NOOP_RESET: NoopResetCpuAllocator,
    REMOTE: RemoteCpuAllocator
}


def get_free_thread_provider(config_manager: ConfigManager) -> FreeThreadProvider:
    free_thread_provider_str = config_manager.get_str(FREE_THREAD_PROVIDER, DEFAULT_FREE_THREAD_PROVIDER)
    free_thread_provider = None

    total_threshold = config_manager.get_float(TOTAL_THRESHOLD, DEFAULT_TOTAL_THRESHOLD)

    if free_thread_provider_str == EMPTY:
        free_thread_provider = EmptyFreeThreadProvider()
    elif free_thread_provider_str == THRESHOLD:
        free_thread_provider = ThresholdFreeThreadProvider(total_threshold)
    elif free_thread_provider_str == OVERSUBSCRIBE:
        free_thread_provider = OversubscribeFreeThreadProvider(total_threshold)

    log.debug("Free thread provider: '{}'".format(free_thread_provider.__class__.__name__))
    return free_thread_provider


def get_fallback_allocator(config_manager) -> FallbackCpuAllocator:
    primary_alloc_str = config_manager.get_str(CPU_ALLOCATOR)
    secondary_alloc_str = config_manager.get_str(FALLBACK_ALLOCATOR, DEFAULT_FALLBACK_ALLOCATOR)

    primary_allocator = get_allocator(primary_alloc_str, config_manager)
    secondary_allocator = get_allocator(secondary_alloc_str, config_manager)

    return FallbackCpuAllocator(primary_allocator, secondary_allocator)


def get_allocator(allocator_str, config_manager):
    if allocator_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(allocator_str, DEFAULT_ALLOCATOR))
        allocator_str = DEFAULT_ALLOCATOR

    free_thread_provider = get_free_thread_provider(config_manager)
    if allocator_str != FORECAST_CPU_IP:
        return CPU_ALLOCATOR_NAME_TO_CLASS_MAP[allocator_str](free_thread_provider)

    return ForecastIPCpuAllocator(
        cpu_usage_predictor_manager=get_cpu_usage_predictor_manager(),
        config_manager=config_manager,
        free_thread_provider=free_thread_provider)
