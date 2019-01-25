import datetime

from titus_isolate import log
from titus_isolate.config.constants import ALLOCATOR_KEY, CPU_ALLOCATORS, DEFAULT_ALLOCATOR, \
    CPU_ALLOCATOR_A, CPU_ALLOCATOR_B, AB_TEST, EC2_INSTANCE_ID, CPU_ALLOCATOR_NAME_TO_CLASS_MAP, AB_MINUTE_OFFSET, \
    DEFAULT_AB_MINUTE_OFFSET, AB_HOUR_FREQUENCY, DEFAULT_AB_HOUR_FREQUENCY, AB_EXTRA_OFFSET, DEFAULT_AB_EXTRA_OFFSET
from titus_isolate.docker.constants import BURST, STATIC
from titus_isolate.utils import get_config_manager

BUCKETS = ["A", "B"]


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def get_allocator_class(config_manager, time=None):
    if time is None:
        time = datetime.datetime.utcnow()

    alloc_str = config_manager.get(ALLOCATOR_KEY)

    if alloc_str == AB_TEST:
        return __get_ab_allocator_class(config_manager, time)
    else:
        return __get_allocator_class(alloc_str)


def __get_allocator_class(allocator_str):
    if allocator_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(allocator_str, DEFAULT_ALLOCATOR))
        allocator_str = DEFAULT_ALLOCATOR

    return CPU_ALLOCATOR_NAME_TO_CLASS_MAP[allocator_str]


def __get_ab_allocator_class(config_manager, time):
    a_allocator_str = config_manager.get(CPU_ALLOCATOR_A)
    b_allocator_str = config_manager.get(CPU_ALLOCATOR_B)

    a_allocator_class = __get_allocator_class(a_allocator_str)
    b_allocator_class = __get_allocator_class(b_allocator_str)

    bucket = get_ab_bucket(config_manager, time)

    if bucket not in BUCKETS:
        log.error("Unexpected A/B bucket specified: '{}', falling back to default: '{}'".format(bucket, DEFAULT_ALLOCATOR))
        return __get_allocator_class("UNDEFINED_AB_BUCKET")

    return {
        "A": a_allocator_class,
        "B": b_allocator_class,
    }[bucket]


def get_ab_bucket(config_manager, time):
    instance_id = config_manager.get(EC2_INSTANCE_ID)
    if instance_id is None:
        log.error("Failed to find: '{}' in config manager, is the environment variable set?".format(EC2_INSTANCE_ID))
        return "UNDEFINED"

    # Take the last character of an instance id turn it into a number and determine whether it's odd or even.
    # An instance id looks like this: i-0cfefd19c9a8db976
    char = instance_id[-1]
    bucket = _get_ab_bucket_int(char, time)
    if bucket == 0:
        return "A"
    else:
        return "B"


def _get_ab_bucket_int(char, time):
    instance_int = ord(char)
    config_manager = get_config_manager()

    minute_offset = config_manager.get(AB_MINUTE_OFFSET, DEFAULT_AB_MINUTE_OFFSET)
    hour_frequency = config_manager.get(AB_HOUR_FREQUENCY, DEFAULT_AB_HOUR_FREQUENCY)
    extra_offset = config_manager.get(AB_EXTRA_OFFSET, DEFAULT_AB_EXTRA_OFFSET)

    randomzation_element = ((time + datetime.timedelta(minutes=minute_offset)).hour // hour_frequency +
                            time.day +
                            extra_offset) % 2

    return (instance_int + randomzation_element) % 2
