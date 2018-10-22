import logging
from queue import Queue
from threading import Thread

log = logging.getLogger()


class WorkloadManager:
    def __init__(self, resource_manager):
        self.__q = Queue()
        self.__resource_manager = resource_manager

        self.__worker_thread = Thread(target=self.__worker)
        self.__worker_thread.daemon = True
        self.__worker_thread.start()

    def add_workloads(self, workloads):
        workload_ids = [w.get_id() for w in workloads]
        log.info("Adding workloads: {}".format(workload_ids))

        def __add_workloads():
            for workload in workloads:
                self.__resource_manager.assign_threads(workload)

        self.__q.put(__add_workloads)

    def remove_workloads(self, workload_ids):
        log.info("Removing workloads: {}".format(workload_ids))

        def __remove_workloads():
            for workload_id in workload_ids:
                self.__resource_manager.free_threads(workload_id)

        self.__q.put(__remove_workloads)

    def get_queue_depth(self):
        return self.__q.qsize()

    def __worker(self):
        while True:
            self.__q.get()()
