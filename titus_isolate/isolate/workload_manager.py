import copy
from threading import Lock
import time

from titus_isolate import log
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.update import get_updates
from titus_isolate.isolate.utils import get_burst_workloads


class WorkloadManager:
    def __init__(self, cpu, cgroup_manager,
            allocator_class=IntegerProgramCpuAllocator,
            fallback_allocator_class=GreedyCpuAllocator):
        self.__lock = Lock()

        self.__error_count = 0
        self.__added_count = 0
        self.__removed_count = 0
        self.__allocator_call_duration_sum_secs = 0
        self.__fallback_allocator_calls_count = 0
        self.__time_bound_ip_allocator_solution_count = 0

        self.__cpu = cpu
        self.__cgroup_manager = cgroup_manager
        self.__workloads = {}
        self.__cpu_allocator = allocator_class(cpu)
        self.__is_ip_allocator_used = False
        self.__fallback_cpu_allocator = None
        if isinstance(self.__cpu_allocator, IntegerProgramCpuAllocator):
            self.__is_ip_allocator_used = True
        if fallback_allocator_class is not None:
            self.__fallback_cpu_allocator = fallback_allocator_class(cpu)
        log.info("Created workload manager with allocator: '{}'".format(self.__cpu_allocator.__class__.__name__))

    def add_workload(self, workload):
        succeeded = self.__update_workload(self.__add_workload, workload, workload.get_id())
        if not succeeded:
            self.__remove_workload(workload.get_id())

    def remove_workload(self, workload_id):
        self.__update_workload(self.__remove_workload, workload_id, workload_id)

    def __update_workload(self, func, arg, workload_id):
        try:
            with self.__lock:
                log.info("Acquired lock for func: {} on workload: {}".format(func.__name__, workload_id))
                start_time = time.time()
                func(arg)
                stop_time = time.time()
                self.__allocator_call_duration_sum_secs = stop_time - start_time
            log.info("Released lock for func: {} on workload: {}".format(func.__name__, workload_id))
            return True
        except:
            self.__error_count += 1
            log.exception("Failed to execute func: {} on workload: {}".format(func.__name__, workload_id))
            return False

    def __call_allocator(self, func_name, *args):
        allocator = self.__cpu_allocator
        try:
            getattr(allocator, func_name)(*args)
            if self.__is_ip_allocator_used and allocator.is_last_call_time_bound():
                self.__time_bound_ip_allocator_solution_count += 1
        except Exception as e:
            if self.__fallback_cpu_allocator is not None:
                allocator = self.__fallback_cpu_allocator
                getattr(allocator, func_name)(*args)
                self.__fallback_allocator_calls_count += 1
            else:
                raise e
        return allocator


    def __add_workload(self, workload):
        log.info("Adding workload: {}".format(workload.get_id()))

        workload_id = workload.get_id()
        self.__workloads[workload_id] = workload

        allocator = self.__cpu_allocator
        if workload.get_type() == STATIC:
            current_cpu = copy.deepcopy(self.get_cpu())
            allocator = self.__call_allocator('assign_threads', workload)
            updates = get_updates(current_cpu, allocator.get_cpu())
            log.info("Found footprint updates: '{}'".format(updates))
            self.__update_static_cpusets(updates)

        if workload.get_type() == BURST:
            self.__cgroup_manager.set_cpuset(workload.get_id(), self.__get_empty_thread_ids())

        self.__cpu = allocator.get_cpu()
        self.__update_burst_cpusets()

        log.info("Added workload: {}".format(workload.get_id()))
        self.__added_count += 1


    def __remove_workload(self, workload_id):
        log.info("Removing workload: {}".format(workload_id))
        if workload_id not in self.__workloads:
            raise ValueError("Attempted to remove unknown workload: '{}'".format(workload_id))

        allocator = self.__call_allocator('free_threads', workload_id)
        self.__workloads.pop(workload_id)

        self.__cpu = allocator.get_cpu()
        self.__update_burst_cpusets()
        log.info("Removed workload: {}".format(workload_id))
        self.__removed_count += 1

    def __update_static_cpusets(self, updates):
        for workload_id, thread_ids in updates.items():
            log.info("updating static workload: '{}'".format(workload_id))
            self.__cgroup_manager.set_cpuset(workload_id, thread_ids)

    def __update_burst_cpusets(self):
        empty_thread_ids = self.__get_empty_thread_ids()
        error_count = 0
        for b_w in get_burst_workloads(self.__workloads.values()):
            log.info("updating burst workload: '{}'".format(b_w.get_id()))
            try:
                self.__cgroup_manager.set_cpuset(b_w.get_id(), empty_thread_ids)
            except:
                error_count += 1
                log.exception("Failed to update burst workload: '{}', maybe it's gone.".format(b_w.get_id()))

        self.__error_count += error_count

    def __get_empty_thread_ids(self):
        return [t.get_id() for t in self.get_cpu().get_empty_threads()]

    def get_allocator_name(self):
        return self.__cpu_allocator.__class__.__name__
    
    def get_allocator(self):
        return self.__cpu_allocator

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
    
    def get_fallback_allocator_calls_count(self):
        return self.__fallback_allocator_calls_count
    
    def get_allocator_call_duration_sum_secs(self):
        return self.__allocator_call_duration_sum_secs

    def get_time_bound_ip_allocator_solution_count(self):
        return self.__time_bound_ip_allocator_solution_count