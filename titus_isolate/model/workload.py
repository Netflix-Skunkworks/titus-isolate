import datetime
import json
from typing import Union

from titus_isolate.event.constants import WORKLOAD_TYPES, BURST, BATCH, SERVICE, STATIC


class Workload:
    def __init__(
            self,
            launch_time,
            identifier,
            thread_count,
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
            opportunistic_thread_count):

        self.__creation_time = datetime.datetime.utcnow()

        if launch_time is None:
            launch_time = -1
        self.__launch_time = int(launch_time)

        self.__identifier = identifier
        self.__thread_count = int(thread_count)
        self.__mem = float(mem)
        self.__disk = float(disk)
        self.__network = float(network)
        self.__app_name = app_name
        self.__owner_email = owner_email
        self.__image = image
        if command is None:
            self.__command = ""
        else:
            self.__command = command
        if entrypoint is None:
            self.__entrypoint = ""
        else:
            self.__entrypoint = entrypoint
        self.__job_type = job_type
        self.__type = workload_type.lower()
        self.__opportunistic_thread_count = int(opportunistic_thread_count)

        if self.__thread_count < 0:
            raise ValueError("A workload must request at least 0 threads.")

        if self.__type not in WORKLOAD_TYPES:
            raise ValueError("Unexpected workload type: '{}', acceptable values are: '{}'".format(
                self.__type, WORKLOAD_TYPES))

        if self.__identifier == BURST:
            raise ValueError("The identifier '{}' is reserved".format(BURST))

    def get_id(self):
        return self.__identifier

    def get_thread_count(self):
        return self.__thread_count

    def get_mem(self):
        return self.__mem

    def get_disk(self):
        return self.__disk

    def get_network(self):
        return self.__network

    def get_app_name(self):
        return self.__app_name

    def get_owner_email(self):
        return self.__owner_email

    def get_image(self):
        return self.__image

    def get_command(self):
        return self.__command

    def get_entrypoint(self):
        return self.__entrypoint

    def get_type(self):
        return self.__type

    def is_burst(self):
        return self.get_type() == BURST

    def is_static(self):
        return self.get_type() == STATIC

    def get_job_type(self):
        return self.__job_type

    def is_batch(self) -> bool:
        return self.__job_type == BATCH

    def is_service(self) -> bool:
        return self.__job_type == SERVICE

    def get_launch_time(self) -> Union[int, None]:
        """
        Launch time of workload in UTC unix seconds
        """
        return self.__launch_time

    # TODO: Remove
    def get_creation_time(self):
        return self.__creation_time

    # TODO: Remove
    def set_creation_time(self, creation_time):
        self.__creation_time = creation_time

    def is_opportunistic(self):
        return self.__opportunistic_thread_count > 0

    def get_opportunistic_thread_count(self):
        return self.__opportunistic_thread_count

    def to_dict(self):
        return {
            "creation_time": str(self.get_creation_time()),
            "launch_time": self.get_launch_time(),
            "id": str(self.get_id()),
            "thread_count": self.get_thread_count(),
            "mem": self.get_mem(),
            "disk": self.get_disk(),
            "network": self.get_network(),
            "app_name": self.get_app_name(),
            "owner_email": self.get_owner_email(),
            "image": self.get_image(),
            "command": self.get_command(),
            "entrypoint": self.get_entrypoint(),
            "job_type": self.get_job_type(),
            "type": self.get_type(),
            "opportunistic_thread_count": self.get_opportunistic_thread_count()
        }

    def __str__(self):
        return json.dumps(self.to_dict())


def deserialize_workload(body: dict) -> Workload:
    return Workload(
        body["launch_time"],
        body["id"],
        body["thread_count"],
        body["mem"],
        body["disk"],
        body["network"],
        body["app_name"],
        body["owner_email"],
        body["image"],
        body["command"],
        body["entrypoint"],
        body["job_type"],
        body["workload_type"],
        body["opportunistic_thread_count"])
