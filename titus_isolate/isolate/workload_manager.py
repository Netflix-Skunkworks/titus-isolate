import copy
import logging
from queue import Queue
from threading import Thread

from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.balance import has_better_isolation
from titus_isolate.isolate.cpu import assign_threads, free_threads
from titus_isolate.isolate.update import get_updates
from titus_isolate.metrics.report import report_metrics

log = logging.getLogger()


class WorkloadManager:
    def __init__(self, cpu, docker_client):
        log.info("Created workload manager")
        self.__q = Queue()
        self.__queue_success_count = 0
        self.__queue_error_count = 0

        self.__cpu = cpu
        self.__docker_client = docker_client

        self.__workloads = {}

        self.__worker_thread = Thread(target=self.__worker)
        self.__worker_thread.daemon = True
        self.__worker_thread.start()

        # Report metrics once on construction to clear initial NaN values
        report_metrics(self)

    def add_workloads(self, workloads):
        for w in workloads:
            def __add_workload():
                log.info("Adding workload: {}".format(w.get_id()))
                self.__workloads[w.get_id()] = w
                new_cpu = copy.deepcopy(self.__cpu)
                self.__assign_workload(new_cpu, w)
                self.__execute_updates(self.__cpu, new_cpu, w)
                log.info("Added workload: {}".format(w.get_id()))

            self.__q.put(__add_workload)

    def __rebalance(self):
        log.info("Attempting re-balance.")
        # Clone the CPU and free all its threads
        sim_cpu = copy.deepcopy(self.__cpu)
        sim_cpu.clear()

        static_workloads = self.__get_static_workloads()
        static_workloads.sort(key=lambda workload: workload.get_thread_count(), reverse=True)

        for w in static_workloads:
            self.__assign_workload(sim_cpu, w)

        if has_better_isolation(self.__cpu, sim_cpu):
            log.info("Found a better placement scenario, updating all workloads.")
            for w in self.__workloads.values():
                self.__execute_updates(self.__cpu, sim_cpu, w)
        else:
            log.info("No improvement in placement found in re-balance, doing nothing.")

    def remove_workloads(self, workload_ids):
        for workload_id in workload_ids:
            def __remove_workload():
                log.info("Removing workload: {}".format(workload_id))
                new_cpu = copy.deepcopy(self.__cpu)
                free_threads(new_cpu, workload_id)
                if self.__workloads.pop(workload_id, None) is None:
                    log.warning("Attempted to remove unknown workload: '{}'".format(workload_id))

                updates = get_updates(self.__cpu, new_cpu)
                log.info("Found footprint updates: '{}'".format(updates))
                if BURST in updates:
                    # If the burst footprint changed due to workloads being removed, then burst workloads
                    # must be updated
                    empty_thread_ids = updates[BURST]
                    burst_workloads_to_update = self.__get_burst_workloads()
                    self.__update_burst_workloads(burst_workloads_to_update, empty_thread_ids)

                self.__cpu = new_cpu
                log.info("Removed workload: {}".format(workload_id))

            self.__q.put(__remove_workload)

    def __get_burst_workloads(self):
        return self.__get_workloads_by_type(self.__workloads.values(), BURST)

    def __get_static_workloads(self):
        return self.__get_workloads_by_type(self.__workloads.values(), STATIC)

    @staticmethod
    def __get_workloads_by_type(workloads, workload_type):
        return [w for w in workloads if w.get_type() == workload_type]

    @staticmethod
    def __assign_workload(new_cpu, workload):
        if workload.get_type() != STATIC:
            return

        assign_threads(new_cpu, workload)

    def __execute_updates(self, cur_cpu, new_cpu, workload):
        updates = get_updates(cur_cpu, new_cpu)
        log.info("Found footprint updates: '{}'".format(updates))

        self.__cpu = new_cpu
        self.__execute_docker_updates(updates, workload)

    def __execute_docker_updates(self, updates, workload):
        # Update new static workloads
        for workload_id, thread_ids in updates.items():
            if workload_id != BURST:
                log.info("updating static workload: '{}'".format(workload_id))
                self.__exec_docker_update(workload_id, thread_ids)

        # If the new workload is a burst workload it should be updated
        empty_thread_ids = [t.get_id() for t in self.__cpu.get_empty_threads()]
        burst_workloads_to_update = [workload]
        if BURST in updates:
            # If the burst footprint has changed ALL burst workloads must be updated
            empty_thread_ids = updates[BURST]
            burst_workloads_to_update = self.__get_burst_workloads()

        self.__update_burst_workloads(burst_workloads_to_update, empty_thread_ids)

    def __update_burst_workloads(self, workloads, thread_ids):
        for b_w in workloads:
            log.info("updating burst workload: '{}'".format(b_w.get_id()))
            self.__exec_docker_update(b_w.get_id(), thread_ids)

    def __exec_docker_update(self, workload_id, thread_ids):
        thread_ids_str = self.__get_thread_ids_str(thread_ids)
        log.info("updating workload: '{}' to cpuset.cpus: '{}'".format(workload_id, thread_ids_str))
        self.__docker_client.containers.get(workload_id).update(cpuset_cpus=thread_ids_str)

    @staticmethod
    def __get_thread_ids_str(thread_ids):
        return ",".join([str(t_id) for t_id in thread_ids])

    def get_queue_depth(self):
        return self.__q.qsize()

    def get_workloads(self):
        return self.__workloads.values()

    def get_cpu(self):
        return self.__cpu

    def get_success_count(self):
        return self.__queue_success_count

    def get_error_count(self):
        return self.__queue_error_count

    def __worker(self):
        while True:
            func = self.__q.get()
            func_name = func.__name__
            log.debug("Executing function: '{}'".format(func_name))

            # If all work has been accomplished and we're not doing a re-balance right now,
            # enqueue a re-balance operation
            if not func_name == self.__rebalance.__name__ and self.get_queue_depth() == 0:
                log.info("Enqueuing re-balance")
                self.__q.put(self.__rebalance)

            try:
                func()
                self.__queue_success_count += 1
                log.debug("Completed function: '{}'".format(func_name))
            except:
                self.__queue_error_count += 1
                log.exception("Failed to execute function: '{}'".format(func_name))

            report_metrics(self)
