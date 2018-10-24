import logging
from queue import Queue
from threading import Thread

from titus_isolate.docker.constants import STATIC, BURST

log = logging.getLogger()


class WorkloadManager:
    def __init__(self, resource_manager):
        self.__q = Queue()
        self.__resource_manager = resource_manager

        self.__workloads = {}

        self.__worker_thread = Thread(target=self.__worker)
        self.__worker_thread.daemon = True
        self.__worker_thread.start()

    def add_workloads(self, workloads):
        workload_ids = [w.get_id() for w in workloads]
        log.info("Adding workloads: {}".format(workload_ids))

        for w in workloads:
            self.__workloads[w.get_id()] = w

        static_workloads = [w for w in workloads if w.get_type() == STATIC]
        static_workloads.sort(key=lambda w: w.get_thread_count(), reverse=True)

        # If any static workloads are being added, then they will change the footprint available to ALL burst
        # workloads.  In this case, all burst workloads must be updated, AFTER static workloads are placed.
        #
        # If only burst workloads are being added, then only the local workloads need to have threads assigned.  This
        # optimization minimizes the number of calls made to the Docker daemon.
        burst_workloads = [w for w in workloads if w.get_type() == BURST]
        if len(static_workloads) > 0:
            burst_workloads = [w for w in self.__workloads.values() if w.get_type() == BURST]

        def __add_workloads():
            for w in static_workloads:
                self.__resource_manager.assign_threads(w)
            for w in burst_workloads:
                self.__resource_manager.assign_threads(w)

        self.__q.put(__add_workloads)

    def remove_workloads(self, workload_ids):
        log.info("Removing workloads: {}".format(workload_ids))

        def __remove_workloads():
            for workload_id in workload_ids:
                self.__resource_manager.free_threads(workload_id)
                if self.__workloads.pop(workload_id, None) is None:
                    log.warning("Attempted to remove unknown workload: '{}'".format(workload_id))

        self.__q.put(__remove_workloads)

    def get_queue_depth(self):
        return self.__q.qsize()

    def __worker(self):
        while True:
            self.__q.get()()
