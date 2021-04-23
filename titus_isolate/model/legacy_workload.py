import datetime
from typing import List

from titus_isolate.event.constants import *
from titus_isolate.model.constants import *
from titus_isolate.model.duration_prediction import DurationPrediction, deserialize_duration_prediction
from titus_isolate.model.workload_interface import Workload


class LegacyWorkload(Workload):

    def __init__(
            self,
            launch_time,
            identifier,
            thread_count,
            job_id,
            mem,
            disk,
            network,
            app_name,
            owner_email,
            image,
            command,
            entrypoint,
            job_type,
            workload_type,
            opportunistic_thread_count,
            duration_predictions):

        self.__creation_time = datetime.datetime.utcnow()

        if launch_time is None:
            launch_time = 0
        self.__launch_time = int(launch_time)

        self.__identifier = identifier
        self.__thread_count = int(thread_count)
        self.__job_id = job_id
        self.__mem = float(mem)
        self.__disk = float(disk)
        self.__network = float(network)
        self.__app_name = app_name
        self.__owner_email = owner_email
        self.__image = image

        if command is None:
            command = ""
        self.__command = command

        if entrypoint is None:
            entrypoint = ""
        self.__entrypoint = entrypoint

        self.__job_type = job_type
        self.__type = workload_type.lower()
        self.__opportunistic_thread_count = int(opportunistic_thread_count)

        if duration_predictions is None:
            duration_predictions = []
        self.__duration_predictions = duration_predictions

        if self.__thread_count < 0:
            raise ValueError("A workload must request at least 0 threads.")

        if self.__type not in WORKLOAD_TYPES:
            raise ValueError("Unexpected workload type: '{}', acceptable values are: '{}'".format(
                self.__type, WORKLOAD_TYPES))

        if self.__identifier == BURST:
            raise ValueError("The identifier '{}' is reserved".format(BURST))

    def get_object_type(self) -> type:
        return type(self)

    def get_id(self) -> str:
        return self.__identifier

    def get_thread_count(self) -> int:
        return self.__thread_count

    def get_job_id(self) -> str:
        return self.__job_id

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
        return self.__type

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

    # TODO: Remove
    def get_creation_time(self):
        return self.__creation_time

    # TODO: Remove
    def set_creation_time(self, creation_time):
        self.__creation_time = creation_time

    def get_launch_time(self) -> int:
        """
        Launch time of workload in UTC unix seconds
        """
        return self.__launch_time

    def is_opportunistic(self):
        return self.__opportunistic_thread_count > 0

    def get_opportunistic_thread_count(self):
        return self.__opportunistic_thread_count

    def get_duration_predictions(self) -> List[DurationPrediction]:
        return self.__duration_predictions

    def to_dict(self):
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
            DURATION_PREDICTIONS_KEY: [p.to_dict() for p in self.get_duration_predictions()]
        }

    def __str__(self):
        return json.dumps(self.to_dict())


def deserialize_legacy_workload(body: dict) -> LegacyWorkload:
    raw_duration_predictions = body.get(DURATION_PREDICTIONS_KEY, [])
    workload = LegacyWorkload(
        body.get(LAUNCH_TIME_KEY, 0),
        body[ID_KEY],
        body[THREAD_COUNT_KEY],
        UNKNOWN_JOB_ID,
        body[MEM_KEY],
        body[DISK_KEY],
        body[NETWORK_KEY],
        body[APP_NAME_KEY],
        body[OWNER_EMAIL_KEY],
        body[IMAGE_KEY],
        body[COMMAND_KEY],
        body[ENTRY_POINT_KEY],
        body[JOB_TYPE_KEY],
        body[WORKLOAD_TYPE_KEY],
        body.get(OPPORTUNISTIC_THREAD_COUNT_KEY, 0),
        [deserialize_duration_prediction(p) for p in raw_duration_predictions])

    # Input example:  "2019-03-23 18:03:50.668041"
    if CREATION_TIME_KEY in body:
        creation_time = datetime.datetime.strptime(body[CREATION_TIME_KEY], '%Y-%m-%d %H:%M:%S.%f')
    else:
        creation_time = datetime.datetime.utcnow()

    workload.set_creation_time(creation_time)
    return workload
