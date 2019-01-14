from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator

PROPERTY_URL_ROOT = 'http://localhost:3002/properties'

# CPU ALLOCATOR CONSTANTS
ALLOCATOR_KEY = 'TITUS_ISOLATE_ALLOCATOR'
AB_TEST = 'AB_TEST'
IP = 'IP'
GREEDY = 'GREEDY'
NOOP = 'NOOP'
DEFAULT_ALLOCATOR = NOOP
CPU_ALLOCATORS = [AB_TEST, IP, GREEDY, NOOP]
CPU_ALLOCATOR_CLASS_MAP = {
    IntegerProgramCpuAllocator.__name__: IP,
    GreedyCpuAllocator.__name__: GREEDY,
    NoopCpuAllocator.__name__: NOOP
}

CPU_ALLOCATOR_A = 'CPU_ALLOCATOR_A'
CPU_ALLOCATOR_B = 'CPU_ALLOCATOR_B'

# CGROUP FILE
WAIT_CGROUP_FILE_KEY = 'TITUS_ISOLATE_WAIT_CGROUP_FILE_SEC'
DEFAULT_WAIT_CGROUP_FILE_SEC = 90

# JSON FILE
WAIT_JSON_FILE_KEY = 'TITUS_ISOLATE_WAIT_JSON_FILE_SEC'
DEFAULT_WAIT_JSON_FILE_SEC = 1

# Static environment variables
EC2_INSTANCE_ID = "EC2_INSTANCE_ID"

PROPERTIES = [
    ALLOCATOR_KEY,
    CPU_ALLOCATOR_A,
    CPU_ALLOCATOR_B,
    EC2_INSTANCE_ID,
    WAIT_CGROUP_FILE_KEY,
    WAIT_JSON_FILE_KEY]


