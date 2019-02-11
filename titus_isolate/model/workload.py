import datetime

from titus_isolate.docker.constants import WORKLOAD_TYPES, BURST


class Workload:
    def __init__(self, identifier, thread_count, workload_type):
        self.__creation_time = datetime.datetime.utcnow()
        self.__identifier = identifier
        self.__thread_count = int(thread_count)
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

    def get_type(self):
        return self.__type

    def get_creation_time(self):
        return self.__creation_time

    def to_dict(self):
        return {
            "creation_time": str(self.__creation_time),
            "id": self.get_id(),
            "type": self.get_type(),
            "thread_count": self.get_thread_count()
        }

    def __str__(self):
        return "id: {}, type: {}, thread_count: {}, creation_time: {}".format(
            self.get_id(), self.get_type(), self.get_thread_count(), self.get_creation_time())
