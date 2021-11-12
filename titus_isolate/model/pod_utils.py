import base64
import gzip
import json
from typing import Optional

from kubernetes import client
from kubernetes.client import V1Pod, V1ContainerStatus, V1Container
from kubernetes.utils import parse_quantity

from titus_isolate import log
from titus_isolate.model.constants import JOB_DESCRIPTOR


def get_start_time(pod: V1Pod) -> Optional[int]:
    """
    Returns the start time of the main container in ms from UTC epoch
    """
    main_container_status = get_main_container_status(pod)
    if main_container_status is None:
        return None

    state = main_container_status.state
    if state is None:
        return None

    if state.running is not None:
        return int(state.running.started_at.timestamp() * 1000)

    return None


def get_main_container_status(pod: V1Pod) -> Optional[V1ContainerStatus]:
    # TODO: Only bother looking for 'main' once fully rolled out
    statuses = [s for s in pod.status.container_statuses if s.name == "main" or s.name == pod.metadata.name]
    if len(statuses) != 1:
        return None

    return statuses[0]


def get_main_container(pod: V1Pod) -> Optional[V1Container]:
    pod_name = pod.metadata.name
    # TODO: Only bother looking for 'main' once fully rolled out
    containers = [c for c in pod.spec.containers if c.name == "main" or c.name == pod_name]

    if len(containers) == 1:
        return containers[0]

    log.info("Failed to find main container for: %s", pod_name)
    return None


def get_job_descriptor(pod: V1Pod) -> Optional[dict]:
    metadata = pod.metadata
    if metadata is None:
        return None

    annotations = metadata.annotations
    if annotations is None:
        return None

    if JOB_DESCRIPTOR not in annotations.keys():
        return None

    return decode_job_descriptor(annotations.get(JOB_DESCRIPTOR))


def decode_job_descriptor(encoded_job_descriptor: str) -> Optional[dict]:
    try:
        jd_bytes = base64.b64decode(encoded_job_descriptor, validate=True)
        jd_bytes = gzip.decompress(jd_bytes)
        return json.loads(jd_bytes.decode("utf-8"))
    except Exception:
        return None


def parse_kubernetes_value(val: str) -> str:
    return str(parse_quantity(val))


def parse_pod(pod: str) -> V1Pod:
    class ResponseStub(object):
        def __init__(self, *args):
            self.data = None

    resp = ResponseStub()
    resp.data = pod

    api_client = client.api_client.ApiClient()
    return api_client.deserialize(response=resp, response_type=V1Pod)


