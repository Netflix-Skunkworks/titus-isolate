import copy

from titus_isolate import log


class Thread:
    def __init__(self, processor_id):
        self.__workload_ids = []
        self.__processor_id = int(processor_id)

        if self.__processor_id < 0:
            raise ValueError("Thread processor ids must be non-negative.")

    def get_id(self):
        return self.__processor_id

    def claim(self, workload_id):
        self.__workload_ids.append(workload_id)

    def free(self, workload_id):
        log.debug("Removing workload: '{}' from thread '{}'".format(workload_id, self.get_id()))
        if workload_id in self.__workload_ids:
            self.__workload_ids.remove(workload_id)

    def clear(self):
        log.debug("Removing all workloads: '{}' from thread '{}'".format(self.__workload_ids, self.get_id()))
        self.__workload_ids = []

    def get_workload_ids(self):
        return copy.deepcopy(self.__workload_ids)

    def is_claimed(self):
        return len(self.get_workload_ids()) > 0
