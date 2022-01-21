import copy
import datetime
import json
from titus_isolate import log

from kubernetes.client import V1Pod

from titus_isolate.kub.constants import LABEL_KEY_JOB_ID, ANNOTATION_KEY_JOB_ID
from titus_isolate.model.constants import CPU, TASK_ID_KEY, THREAD_COUNT_KEY, POD, JOB_ID_KEY
from titus_isolate.model.pod_utils import get_main_container, parse_kubernetes_value
from titus_isolate.model.workload_interface import Workload


class KubernetesWorkload(Workload):

    def __init__(self, pod: V1Pod):
        self.__creation_time = datetime.datetime.utcnow()
        self.__pod = pod

        main_container = get_main_container(pod)
        resource_requests = main_container.resources.requests
        self.__cpus = int(parse_kubernetes_value(resource_requests[CPU]))
        self.__job_id = get_job_id(pod)

    def get_pod(self):
        return copy.deepcopy(self.__pod)

    def get_task_id(self) -> str:
        return self.__pod.metadata.name

    def get_job_id(self) -> str:
        return self.__job_id

    def get_thread_count(self) -> int:
        return self.__cpus

    def to_dict(self) -> dict:
        return {
            TASK_ID_KEY: str(self.get_task_id()),
            JOB_ID_KEY: self.get_job_id(),
            THREAD_COUNT_KEY: self.get_thread_count(),
            POD: self.__get_serializable_pod(self.__pod)
        }

    @staticmethod
    def __json_default(obj):
        if isinstance(obj, datetime.datetime):
            return obj.timestamp()

        return str(obj)

    def __get_serializable_pod(self, pod: V1Pod) -> dict:
        return json.loads(json.dumps(pod.to_dict(), default=self.__json_default))


def get_workload_from_pod(pod: V1Pod) -> KubernetesWorkload:
    return KubernetesWorkload(pod)


def get_job_id(pod: V1Pod) -> str:
    metadata = pod.metadata
    job_id = None

    if metadata.labels is not None:
        job_id = metadata.labels.get(LABEL_KEY_JOB_ID, None)

    if job_id is None:
        # legacy, very few pods launched a while ago
        job_id = metadata.annotations.get(ANNOTATION_KEY_JOB_ID, None)

    if job_id is None:
        raise Exception("failed to extract job ID for pod: {}".format(pod.metadata.name))

    return job_id