import copy
import datetime
import json
from typing import List

from kubernetes.client import V1Pod

from titus_isolate import log
from titus_isolate.event.constants import STATIC, BURST, BATCH, SERVICE
from titus_isolate.model.constants import CPU, MEMORY, TITUS_NETWORK, EPHEMERAL_STORAGE, TITUS_DISK, \
    WORKLOAD_JSON_JOB_TYPE_KEY, OWNER_EMAIL, CPU_BURSTING, WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY, \
    WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY, CREATION_TIME_KEY, LAUNCH_TIME_KEY, ID_KEY, THREAD_COUNT_KEY, MEM_KEY, \
    DISK_KEY, NETWORK_KEY, APP_NAME_KEY, OWNER_EMAIL_KEY, IMAGE_KEY, COMMAND_KEY, ENTRY_POINT_KEY, JOB_TYPE_KEY, \
    WORKLOAD_TYPE_KEY, OPPORTUNISTIC_THREAD_COUNT_KEY, DURATION_PREDICTIONS_KEY, POD
from titus_isolate.model.duration_prediction import DurationPrediction
from titus_isolate.model.pod_utils import get_main_container, parse_kubernetes_value, get_job_descriptor, get_app_name, \
    get_image, get_cmd, get_entrypoint
from titus_isolate.model.utils import get_duration_predictions
from titus_isolate.model.workload_interface import Workload


class KubernetesWorkload(Workload):

    def __init__(self, pod: V1Pod):
        self.__creation_time = datetime.datetime.utcnow()
        self.__pod = pod

        self.__launch_time = pod.metadata.creation_timestamp.timestamp()
        self.__init_resources(pod)
        self.__init_metadata(pod)

    def __init_resources(self, pod: V1Pod):
        main_container = get_main_container(pod)
        resource_requests = main_container.resources.requests

        self.__cpus = int(parse_kubernetes_value(resource_requests[CPU]))
        self.__mem = float(parse_kubernetes_value(resource_requests[MEMORY]))
        self.__network = float(parse_kubernetes_value(resource_requests[TITUS_NETWORK]))
        if EPHEMERAL_STORAGE in resource_requests.keys():
            disk = resource_requests[EPHEMERAL_STORAGE]
        else:
            disk = resource_requests[TITUS_DISK]
        self.__disk = float(parse_kubernetes_value(disk))

    def __init_metadata(self, pod: V1Pod):
        app_name = 'UNKNOWN_APP_NAME'
        image = 'UNKNOWN_IMAGE'
        command = 'UNKNOWN_CMD'
        entrypoint = 'UNKNOWN_ENTRYPOINT'

        job_descriptor = get_job_descriptor(pod)
        log.debug("job_descriptor: %s", job_descriptor)

        if job_descriptor is not None:
            app_name = get_app_name(job_descriptor)
            image = get_image(job_descriptor)
            command = get_cmd(job_descriptor)
            entrypoint = get_entrypoint(job_descriptor)

        metadata = pod.metadata
        job_type = metadata.annotations[WORKLOAD_JSON_JOB_TYPE_KEY]
        owner_email = metadata.annotations[OWNER_EMAIL]
        workload_type_str = metadata.annotations.get(CPU_BURSTING)
        workload_type = STATIC
        if workload_type_str is not None and str(workload_type_str).lower() == "true":
            workload_type = BURST

        opportunistic_cpus = 0
        if WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY in metadata.annotations.keys():
            opportunistic_cpus = metadata.annotations.get(WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY)

        duration_predictions = []
        if WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY in metadata.annotations.keys():
            duration_predictions = \
                get_duration_predictions(metadata.annotations.get(WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY))

        self.__app_name = app_name
        self.__image = image
        self.__command = command
        self.__entrypoint = entrypoint
        self.__job_type = job_type
        self.__owner_email = owner_email
        self.__workload_type = workload_type
        self.__opportunistic_cpus = opportunistic_cpus
        self.__duration_predictions = duration_predictions

    def get_pod(self):
        return copy.deepcopy(self.__pod)

    def get_object_type(self) -> type:
        return type(self)

    def get_id(self) -> str:
        return self.__pod.metadata.name

    def get_thread_count(self) -> int:
        return self.__cpus

    def get_mem(self) -> float:
        return self.__mem

    def get_disk(self) -> float:
        return self.__disk

    def get_network(self) -> float:
        return self.__network

    def get_app_name(self) -> str:
        return self.__app_name

    def get_owner_email(self) -> str:
        return self.__owner_email

    def get_image(self) -> str:
        return self.__image

    def get_command(self) -> str:
        return self.__command

    def get_entrypoint(self) -> str:
        return self.__entrypoint

    def get_type(self) -> str:
        return self.__workload_type

    def is_burst(self) -> bool:
        return self.get_type() == BURST

    def is_static(self) -> bool:
        return self.get_type() == STATIC

    def get_job_type(self) -> str:
        return self.__job_type

    def is_batch(self) -> bool:
        return self.__job_type == BATCH

    def is_service(self) -> bool:
        return self.__job_type == SERVICE

    def get_creation_time(self):
        return self.__creation_time

    def set_creation_time(self, creation_time):
        self.__creation_time = creation_time

    def get_launch_time(self) -> int:
        return self.__launch_time

    def is_opportunistic(self) -> bool:
        return self.__opportunistic_cpus > 0

    def get_opportunistic_thread_count(self) -> int:
        return self.__opportunistic_cpus

    def get_duration_predictions(self) -> List[DurationPrediction]:
        return self.__duration_predictions

    def to_dict(self) -> dict:
        return {
            CREATION_TIME_KEY: str(self.get_creation_time()),
            LAUNCH_TIME_KEY: self.get_launch_time(),
            ID_KEY: str(self.get_id()),
            THREAD_COUNT_KEY: self.get_thread_count(),
            MEM_KEY: self.get_mem(),
            DISK_KEY: self.get_disk(),
            NETWORK_KEY: self.get_network(),
            APP_NAME_KEY: self.get_app_name(),
            OWNER_EMAIL_KEY: self.get_owner_email(),
            IMAGE_KEY: self.get_image(),
            COMMAND_KEY: self.get_command(),
            ENTRY_POINT_KEY: self.get_entrypoint(),
            JOB_TYPE_KEY: self.get_job_type(),
            WORKLOAD_TYPE_KEY: self.get_type(),
            OPPORTUNISTIC_THREAD_COUNT_KEY: self.get_opportunistic_thread_count(),
            DURATION_PREDICTIONS_KEY: [p.to_dict() for p in self.get_duration_predictions()],
            POD: self.__get_serializable_pod(self.__pod)
        }

    @staticmethod
    def __get_serializable_pod(pod: V1Pod) -> str:
        return json.dumps(pod.to_dict(), default=str)


def get_workload_from_pod(pod: V1Pod) -> KubernetesWorkload:
    return KubernetesWorkload(pod)
