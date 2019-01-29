from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator

PROPERTY_URL_ROOT = 'http://localhost:3002/properties'

# CPU ALLOCATOR CONSTANTS
ALLOCATOR_KEY = 'TITUS_ISOLATE_ALLOCATOR'
AB_TEST = 'AB_TEST'
IP = 'IP'
GREEDY = 'GREEDY'
NOOP = 'NOOP'
NOOP_RESET = 'NOOP_RESET'
DEFAULT_ALLOCATOR = NOOP
CPU_ALLOCATORS = [AB_TEST, IP, GREEDY, NOOP, NOOP_RESET]

CPU_ALLOCATOR_NAME_TO_CLASS_MAP = {
    IP: IntegerProgramCpuAllocator,
    GREEDY: GreedyCpuAllocator,
    NOOP: NoopCpuAllocator,
    NOOP_RESET: NoopResetCpuAllocator,
}

CPU_ALLOCATOR_A = 'CPU_ALLOCATOR_A'
CPU_ALLOCATOR_B = 'CPU_ALLOCATOR_B'

# Static environment variables
EC2_INSTANCE_ID = "EC2_INSTANCE_ID"

# GC environment variables
WORKLOAD_GC_INTERVAL_SEC = 'WORKLOAD_GC_INTERVAL_SEC'
DEFAULT_WORKLOAD_GC_INTERVAL_SEC = 5 * 60

PROPERTIES = [
    ALLOCATOR_KEY,
    CPU_ALLOCATOR_A,
    CPU_ALLOCATOR_B,
    EC2_INSTANCE_ID,
    WORKLOAD_GC_INTERVAL_SEC
]


