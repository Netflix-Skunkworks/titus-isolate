import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


class Thread:
    def __init__(self, processor_id):
        self.__workload_id = None
        self.__processor_id = int(processor_id)

        if self.__processor_id < 0:
            raise ValueError("Thread processor ids must be non-negative.")

    def get_id(self):
        return self.__processor_id

    def claim(self, workload_id):
        self.__workload_id = workload_id

    def get_workload_id(self):
        return self.__workload_id

    def clear(self):
        log.info("Releasing thread '{}' for workload '{}'".format(self.get_id(), self.__workload_id))
        self.__workload_id = None

    def is_claimed(self):
        return self.get_workload_id() is not None
