import datetime

from titus_isolate import log
from titus_isolate.allocate.fall_back_cpu_allocator import FallbackCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.forecast_ip_cpu_allocator import ForecastIPCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.allocate.remote_cpu_allocator import RemoteCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, CPU_ALLOCATORS, DEFAULT_ALLOCATOR, \
    CPU_ALLOCATOR_A, CPU_ALLOCATOR_B, AB_TEST, EC2_INSTANCE_ID, IP, GREEDY, NOOP, FORECAST_CPU_IP, \
    NOOP_RESET, FREE_THREAD_PROVIDER, DEFAULT_FREE_THREAD_PROVIDER, EMPTY, THRESHOLD, DEFAULT_TOTAL_THRESHOLD, \
    TOTAL_THRESHOLD, DEFAULT_THRESHOLD_TOTAL_DURATION_SEC, THRESHOLD_TOTAL_DURATION_SEC, DEFAULT_PER_WORKLOAD_THRESHOLD, \
    PER_WORKLOAD_THRESHOLD, DEFAULT_PER_WORKLOAD_DURATION_SEC, PER_WORKLOAD_DURATION_SEC, FALLBACK_ALLOCATOR, \
    DEFAULT_FALLBACK_ALLOCATOR, REMOTE
from titus_isolate.monitor.empty_free_thread_provider import EmptyFreeThreadProvider
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider
from titus_isolate.monitor.threshold_free_thread_provider import ThresholdFreeThreadProvider
from titus_isolate.utils import get_config_manager, get_cpu_usage_predictor_manager, get_workload_monitor_manager

BUCKETS = ["A", "B"]

CPU_ALLOCATOR_NAME_TO_CLASS_MAP = {
    IP: IntegerProgramCpuAllocator,
    GREEDY: GreedyCpuAllocator,
    NOOP: NoopCpuAllocator,
    NOOP_RESET: NoopResetCpuAllocator,
    REMOTE: RemoteCpuAllocator
}


def get_free_thread_provider(config_manager: ConfigManager) -> FreeThreadProvider:
    free_thread_provider_str = config_manager.get(FREE_THREAD_PROVIDER, DEFAULT_FREE_THREAD_PROVIDER)
    free_thread_provider = None

    if free_thread_provider_str == EMPTY:
        free_thread_provider = EmptyFreeThreadProvider()
    elif free_thread_provider_str == THRESHOLD:
        total_threshold = config_manager.get(TOTAL_THRESHOLD, DEFAULT_TOTAL_THRESHOLD)
        total_duration_sec = config_manager.get(THRESHOLD_TOTAL_DURATION_SEC, DEFAULT_THRESHOLD_TOTAL_DURATION_SEC)
        per_workload_threshold = config_manager.get(PER_WORKLOAD_THRESHOLD, DEFAULT_PER_WORKLOAD_THRESHOLD)
        per_workload_duration_sec = config_manager.get(PER_WORKLOAD_DURATION_SEC, DEFAULT_PER_WORKLOAD_DURATION_SEC)

        free_thread_provider = ThresholdFreeThreadProvider(
            total_threshold=total_threshold,
            total_duration_sec=total_duration_sec,
            per_workload_threshold=per_workload_threshold,
            per_workload_duration_sec=per_workload_duration_sec)

    log.debug("Free thread provider: '{}'".format(free_thread_provider.__class__.__name__))
    return free_thread_provider


def get_allocator(config_manager, hour=None) -> FallbackCpuAllocator:
    if hour is None:
        hour = datetime.datetime.utcnow().hour

    primary_alloc_str = config_manager.get(CPU_ALLOCATOR)
    secondary_alloc_str = config_manager.get(FALLBACK_ALLOCATOR, DEFAULT_FALLBACK_ALLOCATOR)

    if primary_alloc_str == AB_TEST:
        primary_allocator = __get_ab_allocator(config_manager, hour)
    else:
        primary_allocator = __get_allocator(primary_alloc_str, config_manager)

    secondary_allocator = __get_allocator(secondary_alloc_str, config_manager)

    return FallbackCpuAllocator(primary_allocator, secondary_allocator)


def __get_allocator(allocator_str, config_manager):
    if allocator_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(allocator_str, DEFAULT_ALLOCATOR))
        allocator_str = DEFAULT_ALLOCATOR

    if allocator_str != FORECAST_CPU_IP:
        free_thread_provider = get_free_thread_provider(config_manager)
        return CPU_ALLOCATOR_NAME_TO_CLASS_MAP[allocator_str](free_thread_provider)

    return ForecastIPCpuAllocator(
        cpu_usage_predictor_manager=get_cpu_usage_predictor_manager(),
        config_manager=get_config_manager(),
        workload_monitor_manager=get_workload_monitor_manager())


def __get_ab_allocator(config_manager, hour):
    a_allocator_str = config_manager.get(CPU_ALLOCATOR_A)
    b_allocator_str = config_manager.get(CPU_ALLOCATOR_B)

    a_allocator = __get_allocator(a_allocator_str, config_manager)
    b_allocator = __get_allocator(b_allocator_str, config_manager)

    bucket = get_ab_bucket(config_manager, hour)

    if bucket not in BUCKETS:
        log.error(
            "Unexpected A/B bucket specified: '{}', falling back to default: '{}'".format(bucket, DEFAULT_ALLOCATOR))
        return __get_allocator("UNDEFINED_AB_BUCKET", config_manager)

    return {
        "A": a_allocator,
        "B": b_allocator,
    }[bucket]


def get_ab_bucket(config_manager, hour):
    instance_id = config_manager.get(EC2_INSTANCE_ID)
    if instance_id is None:
        log.error("Failed to find: '{}' in config manager, is the environment variable set?".format(EC2_INSTANCE_ID))
        return "UNDEFINED"

    # Take the last character of an instance id turn it into a number and determine whether it's odd or even.
    # An instance id looks like this: i-0cfefd19c9a8db976
    char = instance_id[-1]
    bucket = _get_ab_bucket_int(char, hour)
    if bucket == 0:
        return "A"
    else:
        return "B"


def _get_ab_bucket_int(char, hour):
    instance_int = ord(char)
    hour = int(hour / 6)
    int_bucket = (instance_int + (hour % 2)) % 2
    return int_bucket
