# Metrics
DEFAULT_SAMPLE_FREQUENCY_SEC = 6

# Reconciliation
DEFAULT_RECONCILIATION_FREQUENCY_SEC = 60
ENABLE_RECONCILIATION_KEY = 'TITUS_ISOLATE_ENABLE_RECONCILIATION'
DEFAULT_ENABLE_RECONCILIATION = 'true'

# CPU Allocator
CPU_ALLOCATOR = 'TITUS_ISOLATE_ALLOCATOR'
AB_TEST = 'AB_TEST'
IP = 'IP'
FORECAST_CPU_IP = 'FORECAST_CPU_IP'
GREEDY = 'GREEDY'
NOOP = 'NOOP'
NOOP_RESET = 'NOOP_RESET'
DEFAULT_ALLOCATOR = NOOP
CPU_ALLOCATORS = [AB_TEST, IP, FORECAST_CPU_IP, GREEDY, NOOP, NOOP_RESET]

CPU_ALLOCATOR_A = 'CPU_ALLOCATOR_A'
CPU_ALLOCATOR_B = 'CPU_ALLOCATOR_B'

# Free Thread Provider
FREE_THREAD_PROVIDER = 'FREE_THREAD_PROVIDER'
EMPTY = 'EMPTY'
THRESHOLD = 'THRESHOLD'
DEFAULT_FREE_THREAD_PROVIDER = EMPTY

# Threshold Free Thread Provider
TOTAL_THRESHOLD = 'TOTAL_THRESHOLD'
DEFAULT_TOTAL_THRESHOLD = 0.1

THRESHOLD_TOTAL_DURATION_SEC = 'THRESHOLD_TOTAL_DURATION_SEC'
DEFAULT_THRESHOLD_TOTAL_DURATION_SEC = 600

PER_WORKLOAD_THRESHOLD = 'PER_WORKLOAD_THRESHOLD'
DEFAULT_PER_WORKLOAD_THRESHOLD = 0.05

PER_WORKLOAD_DURATION_SEC = 'PER_WORKLOAD_DURATION_SEC'
DEFAULT_PER_WORKLOAD_DURATION_SEC = DEFAULT_SAMPLE_FREQUENCY_SEC

# cgroup File
WAIT_CGROUP_FILE_KEY = 'TITUS_ISOLATE_WAIT_CGROUP_FILE_SEC'
DEFAULT_WAIT_CGROUP_FILE_SEC = 90

# JSON File
WAIT_JSON_FILE_KEY = 'TITUS_ISOLATE_WAIT_JSON_FILE_SEC'
DEFAULT_WAIT_JSON_FILE_SEC = 10

# Blocking isolation wait
TITUS_ISOLATE_BLOCK_SEC = 'TITUS_ISOLATE_BLOCK_SEC'
DEFAULT_TITUS_ISOLATE_BLOCK_SEC = 10

# NUMA balancing
TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING = 'TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING'
DEFAULT_TITUS_ISOLATE_DYNAMIC_NUMA_BALANCING = True

# Event log
EVENT_LOG_FORMAT_STR = 'EVENT_LOG_FORMAT_STR'

# S3 Buckets
DEV = 'prod'
V1 = 'v1'
LATEST = 'latest'

MODEL_BUCKET_FORMAT_STR = 'TITUS_ISOLATE_MODEL_BUCKET_FORMAT_STR'
MODEL_PREFIX_FORMAT_STR = 'TITUS_ISOLATE_MODEL_PREFIX_FORMAT_STR'

MODEL_BUCKET_PREFIX = 'TITUS_ISOLATE_MODEL_BUCKET_PREFIX'
DEFAULT_MODEL_BUCKET_PREFIX = DEV

MODEL_BUCKET_LEAF = 'TITUS_ISOLATE_MODEL_BUCKET_LEAF'
DEFAULT_MODEL_BUCKET_LEAF = LATEST

# Static environment variables
PROPERTY_URL_ROOT = 'http://localhost:3002/properties'
EC2_INSTANCE_ID = "EC2_INSTANCE_ID"

RESTART_PROPERTIES = [
    CPU_ALLOCATOR,
    ENABLE_RECONCILIATION_KEY,
    FREE_THREAD_PROVIDER,
    MODEL_BUCKET_FORMAT_STR,
    MODEL_PREFIX_FORMAT_STR,
    TOTAL_THRESHOLD,
    THRESHOLD_TOTAL_DURATION_SEC,
    PER_WORKLOAD_THRESHOLD,
    PER_WORKLOAD_DURATION_SEC]
