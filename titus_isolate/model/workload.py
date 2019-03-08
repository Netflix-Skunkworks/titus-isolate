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
            image,
            workload_type):

        self.__creation_time = datetime.datetime.utcnow()

        self.__identifier = identifier
        self.__thread_count = int(thread_count)
        self.__mem = mem
        self.__disk = disk
        self.__network = network
        self.__image = image
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

    def get_image(self):
        return self.__image

    def get_type(self):
        return self.__type

    def get_creation_time(self):
        return self.__creation_time

    def to_dict(self):
        return {
            "creation_time": str(self.__creation_time),
            "id": self.get_id(),
            "type": self.get_type(),
            "thread_count": self.get_thread_count(),
            "mem": self.get_mem(),
            "disk": self.get_disk(),
            "network": self.get_network(),
            "image": self.get_image()
        }

    def __str__(self):
        return json.dumps(self.to_dict())
