UNKNOWN_CPU_ALLOCATOR = "UNKNOWN_CPU_ALLOCATOR"
CPU = "cpu"
CPU_ALLOCATOR = "cpu_allocator"
CPU_ARRAY = "cpu_array"

CPU_USAGE = "cpu_usage"
MEM_USAGE = "mem_usage"
METADATA = "metadata"
NET_RECV_USAGE = "net_recv_usage"
NET_TRANS_USAGE = "net_trans_usage"
DISK_USAGE = "disk_usage"

RESOURCE_USAGE_NAMES = [
    CPU_USAGE,
    MEM_USAGE,
    NET_RECV_USAGE,
    NET_TRANS_USAGE,
    DISK_USAGE,
]

WORKLOAD_ALLOCATIONS = "workload_allocations"
WORKLOADS = "workloads"
WORKLOAD_ID = "workload_id"

TITUS_ISOLATE_CELL_HEADER = "X-Titus-Isolate-Cell"
UNKNOWN_CELL = "unknown_cell"
CELL = "cell"
ALLOCATOR_SERVICE_TASK_ID = 'alloc_task_id'  # task id of the service which did run a given allocation
UNKNOWN_ALLOCATOR_SERVICE_TASK_ID = 'unknown_alloc_task_id'
TITUS_TASK_ID = 'TITUS_TASK_ID'

INSTANCE_ID = "instance_id"

FREE_THREAD_IDS = "free_thread_ids"
