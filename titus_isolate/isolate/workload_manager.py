import copy
from threading import Lock, Thread
import time

from titus_isolate import log
from titus_isolate.allocate.burst_cpu_allocator import BurstCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.update import get_updates
from titus_isolate.isolate.utils import get_burst_workloads, free_threads
from titus_isolate.metrics.constants import RUNNING, ADDED_KEY, REMOVED_KEY, SUCCEEDED_KEY, FAILED_KEY, \
    WORKLOAD_COUNT_KEY, ALLOCATOR_CALL_DURATION, PACKAGE_VIOLATIONS_KEY, CORE_VIOLATIONS_KEY, \
    ADDED_TO_FULL_CPU_ERROR_KEY, FULL_CORES_KEY, HALF_CORES_KEY, EMPTY_CORES_KEY
from titus_isolate.metrics.event_log import report_cpu
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.numa.utils import update_numa_balancing


class WorkloadManager(MetricsReporter):

    def __init__(self, cpu, cgroup_manager, static_cpu_allocator):
        self.__reg = None
        self.__lock = Lock()

        self.__static_cpu_allocator = static_cpu_allocator
        self.__burst_cpu_allocator = BurstCpuAllocator()

        self.__error_count = 0
        self.__added_count = 0
        self.__removed_count = 0
        self.__added_to_full_cpu_count = 0
        self.__allocator_call_duration_sum_secs = 0

        self.__cpu = cpu
        self.__cgroup_manager = cgroup_manager
        self.__workloads = {}

        log.info("Created workload manager")

    def add_workload(self, workload):
        update_numa_balancing(workload, self.__cpu)
        succeeded = self.__update_workload(self.__add_workload, workload, workload.get_id())
        if succeeded:
            self.__added_count += 1
        else:
            self.__remove_workload(workload.get_id())

    def remove_workload(self, workload_id):
        self.__cgroup_manager.release_cpuset(workload_id)
        self.__update_workload(self.__remove_workload, workload_id, workload_id)
        self.__removed_count += 1

    def __update_workload(self, func, arg, workload_id):
        try:
            with self.__lock:
                log.info("Acquired lock for func: {} on workload: {}".format(func.__name__, workload_id))
                start_time = time.time()
                func(arg)
                stop_time = time.time()
                self.__allocator_call_duration_sum_secs = stop_time - start_time
                self.__report_cpu_state(self.__cpu)

            log.info("Released lock for func: {} on workload: {}".format(func.__name__, workload_id))
            return True
        except:
            self.__error_count += 1
            log.exception("Failed to execute func: {} on workload: {}".format(func.__name__, workload_id))
            return False

    def __add_workload(self, workload):
        log.info("Assigning '{}' thread(s) to workload: '{}'".format(workload.get_thread_count(), workload.get_id()))

        new_cpu = copy.deepcopy(self.get_cpu())
        workloads = copy.deepcopy(self.__workloads)
        workloads[workload.get_id()] = workload

        # Free threads claimed by BURST workloads, they will be reclaimed below
        for w in get_burst_workloads(workloads.values()):
            free_threads(new_cpu, w.get_id())

        # Assign static workload
        if workload.get_type() == STATIC:
            new_cpu = self.__static_cpu_allocator.assign_threads(new_cpu, workload.get_id(), workloads)

        # Update burst workloads
        new_cpu = self.__burst_cpu_allocator.assign_threads(new_cpu, workload.get_id(), workloads)

        # Apply cpuset updates
        self.__apply_cpuset_updates(copy.deepcopy(self.get_cpu()), new_cpu)

        self.__cpu = new_cpu
        self.__workloads = workloads

    def __remove_workload(self, workload_id):
        log.info("Removing workload: {}".format(workload_id))
        if workload_id not in self.__workloads:
            raise ValueError("Attempted to remove unknown workload: '{}'".format(workload_id))

        new_cpu = copy.deepcopy(self.get_cpu())
        workloads = copy.deepcopy(self.__workloads)
        workload = workloads[workload_id]

        # Free threads claimed by BURST workloads, they will be reclaimed below
        for w in get_burst_workloads(workloads.values()):
            free_threads(new_cpu, w.get_id())

        # Free static workload
        if workload.get_type() == STATIC:
            new_cpu = self.__static_cpu_allocator.free_threads(new_cpu, workload.get_id(), workloads)

        # Update burst workloads
        new_cpu = self.__burst_cpu_allocator.free_threads(new_cpu, workload.get_id(), workloads)

        # Apply cpuset updates
        self.__apply_cpuset_updates(copy.deepcopy(self.get_cpu()), new_cpu)

        workloads.pop(workload_id)
        self.__cpu = new_cpu
        self.__workloads = workloads

    def __apply_cpuset_updates(self, old_cpu, new_cpu):
        updates = get_updates(old_cpu, new_cpu)
        for workload_id, thread_ids in updates.items():
            log.info("updating workload: '{}' to '{}'".format(workload_id, thread_ids))
            self.__cgroup_manager.set_cpuset(workload_id, thread_ids)

    def get_workloads(self):
        return self.__workloads.values()

    def get_isolated_workload_ids(self):
        return self.__cgroup_manager.get_isolated_workload_ids()

    def is_isolated(self, workload_id):
        noop_allocators = [NoopCpuAllocator, NoopResetCpuAllocator]
        for allocator in noop_allocators:
            if isinstance(self.__static_cpu_allocator, allocator):
                return True

        return workload_id in self.get_isolated_workload_ids()

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

    def get_allocator_call_duration_sum_secs(self):
        return self.__allocator_call_duration_sum_secs

    def get_allocator_name(self):
        return self.__static_cpu_allocator.__class__.__name__

    def set_registry(self, registry):
        self.__reg = registry
        self.__static_cpu_allocator.set_registry(registry)
        self.__cgroup_manager.set_registry(registry)

    def __get_full_core_count(self):
        return len(self.__get_cores_with_occupied_threads(2))

    def __get_half_core_count(self):
        return len(self.__get_cores_with_occupied_threads(1))

    def __get_empty_core_count(self):
        return len(self.__get_cores_with_occupied_threads(0))

    def __get_cores_with_occupied_threads(self, thread_count):
        return [c for c in self.get_cpu().get_cores() if self.__get_occupied_thread_count(c) == thread_count]

    @staticmethod
    def __get_occupied_thread_count(core):
        return len([t for t in core.get_threads() if t.is_claimed()])

    @staticmethod
    def __report_cpu_state(cpu):
        log.info("Applied updates resulting in cpu: {}".format(cpu))
        Thread(target=report_cpu, args=[cpu]).start()

    def report_metrics(self, tags):
        self.__reg.gauge(RUNNING, tags).set(1)

        self.__reg.gauge(ADDED_KEY, tags).set(self.get_added_count())
        self.__reg.gauge(REMOVED_KEY, tags).set(self.get_removed_count())
        self.__reg.gauge(SUCCEEDED_KEY, tags).set(self.get_success_count())
        self.__reg.gauge(FAILED_KEY, tags).set(self.get_error_count())
        self.__reg.gauge(WORKLOAD_COUNT_KEY, tags).set(len(self.get_workloads()))
        self.__reg.gauge(ADDED_TO_FULL_CPU_ERROR_KEY, tags).set(self.__added_to_full_cpu_count)

        self.__reg.gauge(ALLOCATOR_CALL_DURATION, tags).set(self.get_allocator_call_duration_sum_secs())

        cross_package_violation_count = len(get_cross_package_violations(self.get_cpu()))
        shared_core_violation_count = len(get_shared_core_violations(self.get_cpu()))
        self.__reg.gauge(PACKAGE_VIOLATIONS_KEY, tags).set(cross_package_violation_count)
        self.__reg.gauge(CORE_VIOLATIONS_KEY, tags).set(shared_core_violation_count)

        # Core occupancy metrics
        self.__reg.gauge(FULL_CORES_KEY, tags).set(self.__get_full_core_count())
        self.__reg.gauge(HALF_CORES_KEY, tags).set(self.__get_half_core_count())
        self.__reg.gauge(EMPTY_CORES_KEY, tags).set(self.__get_empty_core_count())

        # Have the sub-components report metrics
        self.__static_cpu_allocator.report_metrics(tags)
        self.__cgroup_manager.report_metrics(tags)
