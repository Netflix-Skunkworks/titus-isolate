from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.constants import ALLOCATOR_KEY, CPU_ALLOCATORS, IP, DEFAULT_ALLOCATOR, GREEDY, NOOP
from titus_isolate.docker.constants import BURST, STATIC
from titus_isolate.utils import get_logger

log = get_logger()


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def get_allocator_class(config_manager):
    alloc_str = config_manager.get(ALLOCATOR_KEY)

    if alloc_str not in CPU_ALLOCATORS:
        log.error("Unexpected CPU allocator specified: '{}', falling back to default: '{}'".format(alloc_str, DEFAULT_ALLOCATOR))
        alloc_str = DEFAULT_ALLOCATOR

    return {
        IP: IntegerProgramCpuAllocator,
        GREEDY: GreedyCpuAllocator,
        NOOP: NoopCpuAllocator
    }[alloc_str]
