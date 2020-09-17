ADDED_KEY = 'titus-isolate.addedCount'
REMOVED_KEY = 'titus-isolate.removedCount'
REBALANCED_KEY = 'titus-isolate.rebalancedCount'
SUCCEEDED_KEY = 'titus-isolate.succeededCount'
FAILED_KEY = 'titus-isolate.failedCount'
WORKLOAD_PROCESSING_DURATION = 'titus-isolate.workloadProcessingDurationSec'
UPDATE_STATE_DURATION = 'titus-isolate.updateStateDurationSec'
WORKLOAD_COUNT_KEY = 'titus-isolate.workloadCount'
EVENT_SUCCEEDED_KEY = 'titus-isolate.eventSucceeded'
EVENT_FAILED_KEY = 'titus-isolate.eventFailed'
EVENT_PROCESSED_KEY = 'titus-isolate.eventProcessed'

ENQUEUED_COUNT_KEY = 'titus-isolate.enqueuedCount'
DEQUEUED_COUNT_KEY = 'titus-isolate.dequeuedCount'
QUEUE_DEPTH_KEY = 'titus-isolate.queueDepth'
QUEUE_LATENCY_KEY = 'titus-isolate.queueLatency'
ISOLATE_LATENCY_KEY = 'titus-isolate.isolateLatency'

IP_ALLOCATOR_TIMEBOUND_COUNT = 'titus-isolate.ipAllocatorTimeBoundSolutionCount'
FORECAST_REBALANCE_FAILURE_COUNT = 'titus-isolate.forecastRebalanceFailureCount'

WRITE_CPUSET_SUCCEEDED_KEY = 'titus-isolate.writeCpusetSucceeded'
WRITE_CPUSET_FAILED_KEY = 'titus-isolate.writeCpusetFailed'
ISOLATED_WORKLOAD_COUNT = 'titus-isolate.isolatedWorkloadCount'
CPUSET_THREAD_COUNT = 'titus-isolate.cpusetThreadCount'

PACKAGE_VIOLATIONS_KEY = 'titus-isolate.crossPackageViolations'
CORE_VIOLATIONS_KEY = 'titus-isolate.sharedCoreViolations'

EVENT_LOG_SUCCESS = 'titus-isolate.eventLogSuccessCount'
EVENT_LOG_RETRY = 'titus-isolate.eventLogRetryCount'
EVENT_LOG_FAILURE = 'titus-isolate.eventLogFailureCount'

ALLOCATED_SIZE_KEY = 'titus-isolate.allocatedSize'
UNALLOCATED_SIZE_KEY = 'titus-isolate.unallocatedSize'
STATIC_ALLOCATED_SIZE_KEY = 'titus-isolate.staticAllocatedSize'
BURST_ALLOCATED_SIZE_KEY = 'titus-isolate.burstAllocatedSize'
BURST_REQUESTED_SIZE_KEY = 'titus-isolate.burstRequestedSize'
OVERSUBSCRIBED_THREADS_KEY = 'titus-isolate.oversubscribedThreads'
BURSTABLE_THREADS_KEY = 'titus-isolate.burstableThreads'
OVERSUBSCRIBABLE_THREADS_KEY = 'titus-isolate.oversubscribableThreads'

PRIMARY_ASSIGN_COUNT = 'titus-isolate.assignThreadsPrimary'
PRIMARY_FREE_COUNT = 'titus-isolate.freeThreadsPrimary'
PRIMARY_REBALANCE_COUNT = 'titus-isolate.rebalancePrimary'
FALLBACK_ASSIGN_COUNT = 'titus-isolate.assignThreadsFallback'
FALLBACK_FREE_COUNT = 'titus-isolate.freeThreadsFallback'
FALLBACK_REBALANCE_COUNT = 'titus-isolate.rebalanceFallback'

SOLVER_GET_CPU_ALLOCATOR_SUCCESS = 'titus-isolate.getCpuAllocatorSuccessCount'
SOLVER_GET_CPU_ALLOCATOR_FAILURE = 'titus-isolate.getCpuAllocatorFailureCount'
SOLVER_ASSIGN_THREADS_SUCCESS = 'titus-isolate.assignThreadsSuccessCount'
SOLVER_ASSIGN_THREADS_FAILURE = 'titus-isolate.assignThreadsFailureCount'
SOLVER_ASSIGN_THREADS_DURATION = 'titus-isolate.assignThreadsDurationSec'
SOLVER_FREE_THREADS_SUCCESS = 'titus-isolate.freeThreadsSuccessCount'
SOLVER_FREE_THREADS_FAILURE = 'titus-isolate.freeThreadsFailureCount'
SOLVER_FREE_THREADS_DURATION = 'titus-isolate.freeThreadsDurationSec'
SOLVER_REBALANCE_SUCCESS = 'titus-isolate.rebalanceSuccessCount'
SOLVER_REBALANCE_FAILURE = 'titus-isolate.rebalanceFailureCount'
SOLVER_REBALANCE_DURATION = 'titus-isolate.rebalanceThreadsDurationSec'

STATIC_POOL_USAGE_KEY = 'titus-isolate.staticPoolUsage'
BURST_POOL_USAGE_KEY = 'titus-isolate.burstPoolUsage'

RUNNING = 'titus-isolate.running'

RECONCILE_SKIP_COUNT = 'titus-isolate.reconcileSkipCount'
RECONCILE_SUCCESS_COUNT = 'titus-isolate.reconcileSuccessCount'

OVERSUBSCRIBE_FAIL_COUNT = 'titus-isolate.oversubscribeFailCount'
OVERSUBSCRIBE_SKIP_COUNT = 'titus-isolate.oversubscribeSkipCount'
OVERSUBSCRIBE_SUCCESS_COUNT = 'titus-isolate.oversubscribeSuccessCount'
OVERSUBSCRIBE_RECLAIMED_CPU_COUNT = 'titus-isolate.oversubscribeReclaimedCpuCount'
OVERSUBSCRIBE_CONSUMED_CPU_COUNT = 'titus-isolate.oversubscribeConsumedCpuCount'

PARSE_POD_REQUESTED_RESOURCES_FAIL_COUNT = 'titus-isolate.parsePodRequestedResourcesFailCount'