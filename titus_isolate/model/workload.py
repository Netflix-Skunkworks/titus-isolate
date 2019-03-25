import datetime
import json

from titus_isolate.event.constants import WORKLOAD_TYPES, BURST


class Workload:
    def __init__(
            self,
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
            workload_type):

        self.__creation_time = datetime.datetime.utcnow()

        self.__identifier = identifier
        self.__thread_count = int(thread_count)
        self.__mem = mem
        self.__disk = disk
        self.__network = network
        self.__app_name = app_name
        self.__owner_email = owner_email
        self.__image = image
        self.__command = command
        self.__entrypoint = entrypoint
        self.__job_type = job_type
        self.__type = workload_type.lower()

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

    def get_job_type(self):
        return self.__job_type

    def get_creation_time(self):
        return self.__creation_time

    def set_creation_time(self, creation_time):
        self.__creation_time = creation_time

    def to_dict(self):
        return {
            "creation_time": str(self.__creation_time),
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
        }

    def __str__(self):
        return json.dumps(self.to_dict())
