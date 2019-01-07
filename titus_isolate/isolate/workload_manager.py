import copy
from threading import Lock

from titus_isolate import log
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.config.constants import WAIT_CGROUP_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.update import get_updates
from titus_isolate.isolate.utils import get_burst_workloads
from titus_isolate.utils import get_config_manager


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
        log.info("Created workload manager with allocator: '{}'".format(self.__cpu_allocator.__class__.__name__))

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
            self.__error_count += 1
            log.exception("Failed to execute func: {} on workload: {}".format(func.__name__, workload_id))

    def __add_workload(self, workload):
        log.info("Adding workload: {}".format(workload.get_id()))

        file_wait_timeout = int(get_config_manager().get(WAIT_CGROUP_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC))

        workload_id = workload.get_id()
        self.__workloads[workload_id] = workload

        if workload.get_type() == STATIC:
            current_cpu = copy.deepcopy(self.get_cpu())
            self.__cpu_allocator.assign_threads(workload)
            updates = get_updates(current_cpu, self.__cpu_allocator.get_cpu())
            log.info("Found footprint updates: '{}'".format(updates))
            self.cpu = self.__cpu_allocator.get_cpu()
            self.__update_static_cpusets(updates, file_wait_timeout)

        if workload.get_type() == BURST:
            self.__cgroup_manager.set_cpuset(workload.get_id(), self.__get_empty_thread_ids(), file_wait_timeout)

        self.cpu = self.__cpu_allocator.get_cpu()
        self.__update_burst_cpusets()

        log.info("Added workload: {}".format(workload.get_id()))
        self.__added_count += 1

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

    def __update_static_cpusets(self, updates, timeout):
        for workload_id, thread_ids in updates.items():
            log.info("updating static workload: '{}'".format(workload_id))
            self.__cgroup_manager.set_cpuset(workload_id, thread_ids, timeout)

    def __update_burst_cpusets(self):
        empty_thread_ids = self.__get_empty_thread_ids()
        error_count = 0
        for b_w in get_burst_workloads(self.__workloads.values()):
            log.info("updating burst workload: '{}'".format(b_w.get_id()))
            try:
                self.__cgroup_manager.set_cpuset(b_w.get_id(), empty_thread_ids, 0)
            except:
                log.warn("Failed to update burst workload: '{}', maybe it's gone.".format(b_w.get_id()))
                error_count += 1

        self.__error_count += error_count

    def __get_empty_thread_ids(self):
        return [t.get_id() for t in self.get_cpu().get_empty_threads()]

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
