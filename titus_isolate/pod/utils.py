from kubernetes.client import V1Pod
from kubernetes.utils.quantity import parse_quantity

from titus_isolate.crd.model.resources import Resources

SPEC_RESOURCE_CPU_KEY = 'cpu'
SPEC_RESOURCE_MEM_KEY = 'memory'
SPEC_RESOURCE_DISK_KEY = 'ephemeral-storage'
SPEC_RESOURCE_DISK_DEPRECATED_KEY = 'titus/disk'
SPEC_RESOURCE_NET_KEY = 'titus/network'
SPEC_RESOURCE_GPU_KEY = 'nvidia.com/gpu'
ANNOTATION_KEY_JOB_TYPE = 'titus.agent.jobType'
JOB_TYPE_BATCH = 'BATCH'
JOB_TYPE_SERVICE = 'SERVICE'

def get_requested_resources(pod : V1Pod) -> Resources:
    r = pod.spec.containers[0].resources.requests
    disk_str = r.get(SPEC_RESOURCE_DISK_KEY, '')
    if disk_str == '':
        disk_str = r[SPEC_RESOURCE_DISK_DEPRECATED_KEY]

    gpu = 0
    gpu_str = r.get(SPEC_RESOURCE_GPU_KEY, '')
    if gpu_str != '':
        gpu = int(parse_quantity(gpu_str))

    return Resources(
        int(parse_quantity(r[SPEC_RESOURCE_CPU_KEY])),
        int(parse_quantity(r[SPEC_RESOURCE_MEM_KEY])),
        int(parse_quantity(disk_str)),
        int(parse_quantity(r[SPEC_RESOURCE_NET_KEY])),
        gpu
    )

def is_batch_pod(pod : V1Pod) -> bool:
    t = pod.metadata.annotations.get(ANNOTATION_KEY_JOB_TYPE, None)
    return t == JOB_TYPE_BATCH

def is_service_pod(pod : V1Pod) -> bool:
    t = pod.metadata.annotations.get(ANNOTATION_KEY_JOB_TYPE, None)
    return t == JOB_TYPE_SERVICE    