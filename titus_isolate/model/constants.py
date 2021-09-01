WORKLOAD_JSON_FORMAT = '/var/lib/titus-environments/{}.json'
WORKLOAD_ENV_FORMAT = '/var/lib/titus-environments/{}.env'
WORKLOAD_ENV_LINE_REGEXP = r'(\w+)="([^"]*)"'

WORKLOAD_ENV_CPU_KEY = 'TITUS_NUM_CPU'
WORKLOAD_ENV_JOB_ID = 'TITUS_JOB_ID'

# Prediction annotations
WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY = 'titus.agent.runtimePredictionsAvailable'

WORKLOAD_JSON_READ_ATTEMPTS = 5
WORKLOAD_JSON_READ_SLEEP_SECONDS = 0.1

WORKLOAD_JSON_RUNSTATE_KEY = 'runState'
WORKLOAD_JSON_LAUNCHTIME_KEY = 'launchTimeUnixSec'

NAME = "name"
JOB_DESCRIPTOR = "jobDescriptor"
CPU = "cpu"

TASK_ID_KEY = "task_id"
JOB_ID_KEY = "job_id"
THREAD_COUNT_KEY = "thread_count"
UNKNOWN_JOB_ID = "unknown"
POD = "pod"

# Custom Resource Definitions
CUSTOM_RESOURCE_GROUP = 'titus.netflix.com'
PREDICTED_USAGE_RESOURCE_VERSION = 'v3'
PREDICTED_USAGE_RESOURCE_API_VERSION = CUSTOM_RESOURCE_GROUP + '/' + PREDICTED_USAGE_RESOURCE_VERSION
