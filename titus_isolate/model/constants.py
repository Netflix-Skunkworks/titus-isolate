WORKLOAD_JSON_FORMAT = '/var/lib/titus-environments/{}.json'
WORKLOAD_ENV_FORMAT = '/var/lib/titus-environments/{}.env'
WORKLOAD_ENV_LINE_REGEXP = r'(\w+)="([^"]*)"'

WORKLOAD_ENV_CPU_KEY = 'TITUS_NUM_CPU'
WORKLOAD_ENV_MEM_KEY = 'TITUS_NUM_MEM'
WORKLOAD_ENV_DISK_KEY = 'TITUS_NUM_DISK'
WORKLOAD_ENV_NETWORK_KEY = 'TITUS_NUM_NETWORK_BANDWIDTH'
WORKLOAD_ENV_JOB_ID = 'TITUS_JOB_ID'

WORKLOAD_JSON_APP_NAME_KEY = 'appName'
WORKLOAD_JSON_PASSTHROUGH_KEY = 'passthroughAttributes'
WORKLOAD_JSON_OWNER_KEY = 'titus.agent.ownerEmail'
WORKLOAD_JSON_IMAGE_KEY = 'fullyQualifiedImage'
WORKLOAD_JSON_IMAGE_DIGEST_KEY = 'imageDigest'
WORKLOAD_JSON_PROCESS_KEY = 'process'
WORKLOAD_JSON_COMMAND_KEY = 'command'
WORKLOAD_JSON_ENTRYPOINT_KEY = 'entrypoint'
WORKLOAD_JSON_JOB_TYPE_KEY = 'titus.agent.jobType'
WORKLOAD_JSON_CPU_BURST_KEY = 'allowCpuBursting'

# Prediction annotations
WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY = 'titus.agent.runtimePredictionsAvailable'

WORKLOAD_JSON_READ_ATTEMPTS = 5
WORKLOAD_JSON_READ_SLEEP_SECONDS = 0.1

WORKLOAD_JSON_RUNSTATE_KEY = 'runState'
WORKLOAD_JSON_LAUNCHTIME_KEY = 'launchTimeUnixSec'

CPU = "cpu"
MEMORY = "memory"
EPHEMERAL_STORAGE = "ephemeral-storage"
TITUS_DISK = "titus/disk"
TITUS_NETWORK = "titus/network"

APP_NAME = "applicationName"
COMMAND = "command"
CONTAINER = "container"
CPU_BURSTING = "titusParameter.agent.allowCpuBursting"
ENTRYPOINT = "entryPoint"
IMAGE = "image"
JOB_DESCRIPTOR = "jobDescriptor"
NAME = "name"
OWNER_EMAIL = "titus.agent.ownerEmail"

CREATION_TIME_KEY = "creation_time"
LAUNCH_TIME_KEY = "launch_time"
ID_KEY = "id"
THREAD_COUNT_KEY = "thread_count"
MEM_KEY = "mem"
DISK_KEY = "disk"
NETWORK_KEY = "network"
APP_NAME_KEY = "app_name"
OWNER_EMAIL_KEY = "owner_email"
IMAGE_KEY = "image"
COMMAND_KEY = "command"
ENTRY_POINT_KEY = "entrypoint"
JOB_TYPE_KEY = "job_type"
UNKNOWN_JOB_ID = "unknown"
WORKLOAD_TYPE_KEY = "type"
OPPORTUNISTIC_THREAD_COUNT_KEY = "opportunistic_thread_count"
DURATION_PREDICTIONS_KEY = "duration_predictions"
POD = "pod"

# Custom Resource Definitions
CUSTOM_RESOURCE_GROUP = 'titus.netflix.com'
OPPORTUNISTIC_RESOURCE_VERSION = 'v1'
PREDICTED_USAGE_RESOURCE_VERSION = 'v3'
OPPORTUNISTIC_RESOURCE_API_VERSION = CUSTOM_RESOURCE_GROUP + '/' + OPPORTUNISTIC_RESOURCE_VERSION
PREDICTED_USAGE_RESOURCE_API_VERSION = CUSTOM_RESOURCE_GROUP + '/' + PREDICTED_USAGE_RESOURCE_VERSION
OPPORTUNISTIC_RESOURCE_TTL = 'crd.titus.netflix.com/ttl'
