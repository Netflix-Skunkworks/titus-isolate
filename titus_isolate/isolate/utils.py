import datetime

from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.config.constants import ALLOCATOR_KEY, CPU_ALLOCATORS, DEFAULT_ALLOCATOR, \
    CPU_ALLOCATOR_A, CPU_ALLOCATOR_B, AB_TEST, EC2_INSTANCE_ID, IP, GREEDY, NOOP, \
    NOOP_RESET
from titus_isolate.docker.constants import BURST, STATIC

BUCKETS = ["A", "B"]

CPU_ALLOCATOR_NAME_TO_CLASS_MAP = {
    IP: IntegerProgramCpuAllocator,
    GREEDY: GreedyCpuAllocator,
    NOOP: NoopCpuAllocator,
    NOOP_RESET: NoopResetCpuAllocator,
}


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def get_sorted_workloads(workloads):
    return sorted(workloads, key=lambda w: w.get_creation_time())


def get_allocator(config_manager, hour=None):
    if hour is None:
        hour = datetime.datetime.utcnow().hour

    alloc_str = config_manager.get(ALLOCATOR_KEY)

    if alloc_str == AB_TEST:
        return __get_ab_allocator(config_manager, hour)
    else:
        return __get_allocator(alloc_str)


def __get_allocator(allocator_str):
    if allocator_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(allocator_str, DEFAULT_ALLOCATOR))
        allocator_str = DEFAULT_ALLOCATOR

    return CPU_ALLOCATOR_NAME_TO_CLASS_MAP[allocator_str]()


def __get_ab_allocator(config_manager, hour):
    a_allocator_str = config_manager.get(CPU_ALLOCATOR_A)
    b_allocator_str = config_manager.get(CPU_ALLOCATOR_B)

    a_allocator = __get_allocator(a_allocator_str)
    b_allocator = __get_allocator(b_allocator_str)

    bucket = get_ab_bucket(config_manager, hour)

    if bucket not in BUCKETS:
        log.error("Unexpected A/B bucket specified: '{}', falling back to default: '{}'".format(bucket, DEFAULT_ALLOCATOR))
        return __get_allocator("UNDEFINED_AB_BUCKET")

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
