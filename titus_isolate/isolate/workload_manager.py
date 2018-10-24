import copy
import logging
from queue import Queue
from threading import Thread

from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.balance import has_better_isolation
from titus_isolate.isolate.resource_manager import ResourceManager

log = logging.getLogger()


class WorkloadManager:
    def __init__(self, resource_manager):
        self.__q = Queue()
        self.__resource_manager = resource_manager

        self.__workloads = {}

        self.__worker_thread = Thread(target=self.__worker)
        self.__worker_thread.daemon = True
        self.__worker_thread.start()

    def add_workloads(self, workloads, async=True):
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

        if async:
            self.__q.put(__add_workloads)
        else:
            __add_workloads()

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

    def __rebalance(self):
        log.info("Attempting re-balance.")
        # Clone the CPU and free all its threads
        sim_cpu = copy.deepcopy(self.__get_cpu())
        sim_cpu.clear()

        # Simulate placement of all workloads at once to achieve an ideal result
        sim_wm = WorkloadManager(ResourceManager(cpu=sim_cpu, docker_client=None, dry_run=True))
        sim_wm.add_workloads(self.__workloads.values(), async=False)
        new_cpu = sim_wm.__get_cpu()

        if has_better_isolation(self.__get_cpu(), new_cpu):
            log.info("Found a better placement option, re-adding all workloads.")
            workloads = self.__workloads.values()
            self.__workloads = {}
            self.__get_cpu().clear()
            self.add_workloads(workloads)
        else:
            log.info("Re-balance is a NOOP, due to NOT finding any improvement.")

    def __get_cpu(self):
        return self.__resource_manager.get_cpu()

    def __worker(self):
        while True:
            func = self.__q.get()
            func_name = func.__name__
            log.debug("Executing function: '{}'".format(func_name))

            # If all work has been accomplished and we're not doing a re-balance right now,
            # enqueue a re-balance operation
            if not func_name == self.__rebalance.__name__ and self.get_queue_depth() == 0:
                self.__q.put(self.__rebalance)

            func()
