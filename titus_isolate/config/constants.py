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

# CGROUP FILE
WAIT_CGROUP_FILE_KEY = 'TITUS_ISOLATE_WAIT_CGROUP_FILE_SEC'
DEFAULT_WAIT_CGROUP_FILE_SEC = 90

# JSON FILE
WAIT_JSON_FILE_KEY = 'TITUS_ISOLATE_WAIT_JSON_FILE_SEC'
DEFAULT_WAIT_JSON_FILE_SEC = 1

# Static environment variables
EC2_INSTANCE_ID = "EC2_INSTANCE_ID"

# A/B Test randomization variables
AB_MINUTE_OFFSET = 'AB_MINUTE_OFFSET'
AB_HOUR_FREQUENCY = 'AB_HOUR_FREQUENCY'
AB_EXTRA_OFFSET = 'AB_EXTRA_OFFSET'
DEFAULT_AB_MINUTE_OFFSET = 0
DEFAULT_AB_HOUR_FREQUENCY = 6
DEFAULT_AB_EXTRA_OFFSET = 0

PROPERTIES = [
    ALLOCATOR_KEY,
    AB_MINUTE_OFFSET,
    AB_HOUR_FREQUENCY,
    AB_EXTRA_OFFSET,
    CPU_ALLOCATOR_A,
    CPU_ALLOCATOR_B,
    EC2_INSTANCE_ID,
    WAIT_CGROUP_FILE_KEY,
    WAIT_JSON_FILE_KEY]
