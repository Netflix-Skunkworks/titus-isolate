import copy
from threading import Lock

from titus_isolate.isolate.balance import has_better_isolation
from titus_isolate.isolate.cpu import IntegerProgramCpuAllocator
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.update import get_updates
from titus_isolate.isolate.utils import get_static_workloads, get_burst_workloads
from titus_isolate.utils import get_logger

log = get_logger()


class WorkloadManager:
    def __init__(self, cpu, cgroup_manager, allocator_class=IntegerProgramCpuAllocator):
        self.__lock = Lock()

        self.__error_count = 0
        self.__added_count = 0
        self.__removed_count = 0

        self.__cpu = cpu
        self.__cgroup_manager = cgroup_manager
        self.__workloads = {}
        self.__cpu_allocator = allocator_class(cpu)
        log.info("Created workload manager")

    def add_workload(self, workload):
        self.__update_workload(self.__add_workload, workload, workload.get_id())

    def remove_workload(self, workload_id):
        self.__update_workload(self.__remove_workload, workload_id, workload_id)

    def __update_workload(self, func, arg, workload_id):
        try:
            with self.__lock:
                log.info("Acquired lock for func: {} on workload: {}".format(func.__name__, workload_id))
                func(arg)
            log.info("Released lock for func: {} on workload: {}".format(func.__name__, workload_id))
        except:
            log.exception("Failed to execute func: {} on workload: {}".format(func.__name__, workload_id))
            self.__error_count += 1

    def __add_workload(self, workload):
        log.info("Adding workload: {}".format(workload.get_id()))

        self.__workloads[workload.get_id()] = workload

        if workload.get_type() == STATIC:
            current_cpu = copy.deepcopy(self.get_cpu())
            self.__cpu_allocator.assign_threads(workload)
            updates = get_updates(current_cpu, self.__cpu_allocator.get_cpu())
            log.info("Found footprint updates: '{}'".format(updates))
            self.cpu = self.__cpu_allocator.get_cpu()
            self.__update_static_cpusets(updates)
        
        self.cpu = self.__cpu_allocator.get_cpu()
        self.__update_burst_cpusets()

        log.info("Added workload: {}".format(workload.get_id()))
        self.__added_count += 1
        # todo: add metrics

    def __remove_workload(self, workload_id):
        log.info("Removing workload: {}".format(workload_id))
        if workload_id not in self.__workloads:
            raise ValueError("Attempted to remove unknown workload: '{}'".format(workload_id))

        self.__cpu_allocator.free_threads(workload_id)

        self.cpu = self.__cpu_allocator.get_cpu()
        self.__workloads.pop(workload_id)

        self.__update_burst_cpusets()
        log.info("Removed workload: {}".format(workload_id))
        self.__removed_count += 1
        # todo: add metrics

    def __update_static_cpusets(self, updates):
        for workload_id, thread_ids in updates.items():
            log.info("updating static workload: '{}'".format(workload_id))
            self.__cgroup_manager.set_cpuset(workload_id, thread_ids)

    def __update_burst_cpusets(self):
        empty_thread_ids = [t.get_id() for t in self.get_cpu().get_empty_threads()]
        for b_w in get_burst_workloads(self.__workloads.values()):
            log.info("updating burst workload: '{}'".format(b_w.get_id()))
            self.__cgroup_manager.set_cpuset(b_w.get_id(), empty_thread_ids)

    def get_workloads(self):
        return self.__workloads.values()

    def get_cpu(self):
        return self.__cpu

    def get_added_count(self):
        return self.__added_count

    def get_removed_count(self):
        return self.__removed_count

    def get_success_count(self):
        return self.get_added_count() + \
               self.get_removed_count()

    def get_error_count(self):
        return self.__error_count
