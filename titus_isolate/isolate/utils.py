from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.constants import ALLOCATOR_KEY, CPU_ALLOCATORS, IP, DEFAULT_ALLOCATOR, GREEDY, NOOP, \
    CPU_ALLOCATOR_A, CPU_ALLOCATOR_B, AB_TEST, EC2_INSTANCE_ID
from titus_isolate.docker.constants import BURST, STATIC

BUCKETS = ["A", "B"]


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def get_allocator_class(config_manager):
    alloc_str = config_manager.get(ALLOCATOR_KEY)

    if alloc_str == AB_TEST:
        return __get_ab_allocator_class(config_manager)
    else:
        return __get_allocator_class(alloc_str)


def __get_allocator_class(allocator_str):
    if allocator_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(allocator_str, DEFAULT_ALLOCATOR))
        allocator_str = DEFAULT_ALLOCATOR

    return {
        IP: IntegerProgramCpuAllocator,
        GREEDY: GreedyCpuAllocator,
        NOOP: NoopCpuAllocator
    }[allocator_str]


def __get_ab_allocator_class(config_manager):
    a_allocator_str = config_manager.get(CPU_ALLOCATOR_A)
    b_allocator_str = config_manager.get(CPU_ALLOCATOR_B)

    a_allocator_class = __get_allocator_class(a_allocator_str)
    b_allocator_class = __get_allocator_class(b_allocator_str)

    bucket = get_ab_bucket(config_manager)

    if bucket not in BUCKETS:
        log.error("Unexpected A/B bucket specified: '{}', falling back to default: '{}'".format(bucket, DEFAULT_ALLOCATOR))
        return __get_allocator_class("UNDEFINED_AB_BUCKET")

    return {
        "A": a_allocator_class,
        "B": b_allocator_class,
    }[bucket]


def get_ab_bucket(config_manager):

    instance_id = config_manager.get(EC2_INSTANCE_ID)
    if instance_id is None:
        log.error("Failed to find: '{}' in config manager, is the environment variable set?".format(EC2_INSTANCE_ID))
        return "UNDEFINED"

    # Take the last character of an instance id turn it into a number and determine whether it's odd or even.
    # An instance id looks like this: i-0cfefd19c9a8db976
    bucket = ord(instance_id[-1]) % 2
    if bucket == 0:
        return "A"
    else:
        return "B"
