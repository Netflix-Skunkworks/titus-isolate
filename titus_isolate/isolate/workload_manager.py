import copy
from threading import Lock
import time

from titus_isolate import log

from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.constants import CPU_ALLOCATOR
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.config.constants import EC2_INSTANCE_ID
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.metrics_utils import get_static_allocated_size, get_burst_allocated_size, \
    get_burst_request_size, get_oversubscribed_thread_count, get_allocated_size, get_unallocated_size
from titus_isolate.isolate.update import get_updates
from titus_isolate.metrics.constants import RUNNING, ADDED_KEY, REMOVED_KEY, SUCCEEDED_KEY, FAILED_KEY, \
    WORKLOAD_COUNT_KEY, ALLOCATOR_CALL_DURATION, PACKAGE_VIOLATIONS_KEY, CORE_VIOLATIONS_KEY, \
    ADDED_TO_FULL_CPU_ERROR_KEY, OVERSUBSCRIBED_THREADS_KEY, \
    STATIC_ALLOCATED_SIZE_KEY, BURST_ALLOCATED_SIZE_KEY, BURST_REQUESTED_SIZE_KEY, ALLOCATED_SIZE_KEY, \
    UNALLOCATED_SIZE_KEY, REBALANCED_KEY
from titus_isolate.metrics.event_log import report_cpu_event
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.utils import visualize_cpu_comparison
from titus_isolate.numa.utils import update_numa_balancing
from titus_isolate.utils import get_workload_monitor_manager, get_config_manager


class WorkloadManager(MetricsReporter):

    def __init__(self, cpu: Cpu, cgroup_manager: CgroupManager, cpu_allocator: CpuAllocator):

        self.__reg = None
        self.__lock = Lock()
        self.__instance_id = get_config_manager().get_str(EC2_INSTANCE_ID)

        self.__cpu_allocator = cpu_allocator

        self.__error_count = 0
        self.__added_count = 0
        self.__removed_count = 0
        self.__rebalanced_count = 0
        self.__added_to_full_cpu_count = 0
        self.__allocator_call_duration_sum_secs = 0

        self.__cpu = cpu
        self.__cgroup_manager = cgroup_manager
        self.__wmm = get_workload_monitor_manager()
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

    def rebalance(self):
        succeeded = self.__update_workload(self.__rebalance, None, None)
        if succeeded:
            self.__rebalanced_count += 1

    def __update_workload(self, func, arg, workload_id):
        try:
            with self.__lock:
                log.debug("Acquired lock for func: {} on workload: {}".format(func.__name__, workload_id))
                start_time = time.time()
                func(arg)
                stop_time = time.time()
                self.__allocator_call_duration_sum_secs = stop_time - start_time

            log.debug("Released lock for func: {} on workload: {}".format(func.__name__, workload_id))
            return True
        except:
            self.__error_count += 1
            log.exception("Failed to execute func: {} on workload: {}".format(func.__name__, workload_id))
            return False

    def __add_workload(self, workload):
        log.info("Assigning '{}' thread(s) to workload: '{}'".format(workload.get_thread_count(), workload.get_id()))

        workload_map = self.get_workload_map_copy()
        workload_map[workload.get_id()] = workload

        request = self.__get_threads_request(workload.get_id(), workload_map, "assign")
        response = self.__cpu_allocator.assign_threads(request)

        self.__update_state(response.get_cpu(), workload_map)
        report_cpu_event(request, response)

    def __remove_workload(self, workload_id):
        log.info("Removing workload: {}".format(workload_id))
        if workload_id not in self.__workloads:
            log.error("Attempted to remove unknown workload: '{}'".format(workload_id))
            return

        workload_map = self.get_workload_map_copy()

        request = self.__get_threads_request(workload_id, workload_map, "free")
        response = self.__cpu_allocator.free_threads(request)

        workload_map.pop(workload_id)
        self.__update_state(response.get_cpu(), workload_map)
        report_cpu_event(request, response)

    def __rebalance(self, dummy):
        request = self.__get_rebalance_request()
        response = self.__cpu_allocator.rebalance(request)

        self.__update_state(response.get_cpu(), request.get_workloads())
        report_cpu_event(request, response)

    def __update_state(self, new_cpu, new_workloads):
        old_cpu = self.get_cpu_copy()
        self.__apply_cpuset_updates(old_cpu, new_cpu)
        self.__cpu = new_cpu
        self.__workloads = new_workloads

        if old_cpu != new_cpu:
            self.__report_cpu_state(old_cpu, new_cpu)

    def __apply_cpuset_updates(self, old_cpu, new_cpu):
        updates = get_updates(old_cpu, new_cpu)
        for workload_id, thread_ids in updates.items():
            log.info("updating workload: '{}' to '{}'".format(workload_id, thread_ids))
            self.__cgroup_manager.set_cpuset(workload_id, thread_ids)

    def __get_request_metadata(self, request_type) -> dict:
        config_manager = get_config_manager()
        return {
            "type": request_type,
            "instance_id": self.__instance_id,
            "region": config_manager.get_region(),
            "environment": config_manager.get_environment(),
            "stack": config_manager.get_stack()
        }

    def __get_cpu_usage(self) -> dict:
        return self.__wmm.get_cpu_usage(seconds=3600, agg_granularity_secs=60)

    def __get_threads_request(self, workload_id, workload_map, request_type):
        return AllocateThreadsRequest(
            self.get_cpu_copy(),
            workload_id,
            workload_map,
            self.__get_cpu_usage(),
            self.__get_request_metadata(request_type))

    def __get_rebalance_request(self):
        return AllocateRequest(
            self.get_cpu_copy(),
            self.get_workload_map_copy(),
            self.__get_cpu_usage(),
            self.__get_request_metadata("rebalance"))

    def get_workloads(self):
        return list(self.__workloads.values())

    def get_workload_map_copy(self):
        return copy.deepcopy(self.__workloads)

    def get_isolated_workload_ids(self):
        return self.__cgroup_manager.get_isolated_workload_ids()

    def is_isolated(self, workload_id):
        noop_allocators = [NoopCpuAllocator, NoopResetCpuAllocator]
        for allocator in noop_allocators:
            if isinstance(self.__cpu_allocator, allocator):
                return True

        return workload_id in self.get_isolated_workload_ids()

    def get_cpu(self):
        return self.__cpu

    def get_cpu_copy(self):
        return copy.deepcopy(self.__cpu)

    def get_added_count(self):
        return self.__added_count

    def get_removed_count(self):
        return self.__removed_count

    def get_rebalanced_count(self):
        return self.__rebalanced_count

    def get_success_count(self):
        return self.get_added_count() + \
               self.get_removed_count() + \
               self.get_rebalanced_count()

    def get_error_count(self):
        return self.__error_count

    def get_allocator_call_duration_sum_secs(self):
        return self.__allocator_call_duration_sum_secs

    def get_allocator_name(self):
        return self.__cpu_allocator.get_name()

    def set_registry(self, registry):
        self.__reg = registry
        self.__cpu_allocator.set_registry(registry)
        self.__cgroup_manager.set_registry(registry)

    def __report_cpu_state(self, old_cpu, new_cpu):
        log.info(visualize_cpu_comparison(old_cpu, new_cpu))

    def report_metrics(self, tags):
        cpu = self.get_cpu_copy()
        workload_map = self.get_workload_map_copy()

        self.__reg.gauge(RUNNING, tags).set(1)

        self.__reg.gauge(ADDED_KEY, tags).set(self.get_added_count())
        self.__reg.gauge(REMOVED_KEY, tags).set(self.get_removed_count())
        self.__reg.gauge(REBALANCED_KEY, tags).set(self.get_rebalanced_count())
        self.__reg.gauge(SUCCEEDED_KEY, tags).set(self.get_success_count())
        self.__reg.gauge(FAILED_KEY, tags).set(self.get_error_count())
        self.__reg.gauge(WORKLOAD_COUNT_KEY, tags).set(len(self.get_workloads()))
        self.__reg.gauge(ADDED_TO_FULL_CPU_ERROR_KEY, tags).set(self.__added_to_full_cpu_count)

        self.__reg.gauge(ALLOCATOR_CALL_DURATION, tags).set(self.get_allocator_call_duration_sum_secs())

        cross_package_violation_count = len(get_cross_package_violations(cpu))
        shared_core_violation_count = len(get_shared_core_violations(cpu))
        self.__reg.gauge(PACKAGE_VIOLATIONS_KEY, tags).set(cross_package_violation_count)
        self.__reg.gauge(CORE_VIOLATIONS_KEY, tags).set(shared_core_violation_count)

        # Allocation / Request sizes
        self.__reg.gauge(ALLOCATED_SIZE_KEY, tags).set(get_allocated_size(cpu))
        self.__reg.gauge(UNALLOCATED_SIZE_KEY, tags).set(get_unallocated_size(cpu))
        self.__reg.gauge(STATIC_ALLOCATED_SIZE_KEY, tags).set(get_static_allocated_size(cpu, workload_map))
        self.__reg.gauge(BURST_ALLOCATED_SIZE_KEY, tags).set(get_burst_allocated_size(cpu, workload_map))
        self.__reg.gauge(BURST_REQUESTED_SIZE_KEY, tags).set(get_burst_request_size(list(workload_map.values())))
        self.__reg.gauge(OVERSUBSCRIBED_THREADS_KEY, tags).set(get_oversubscribed_thread_count(cpu, workload_map))

        # Have the sub-components report metrics
        self.__cpu_allocator.report_metrics(tags)
        self.__cgroup_manager.report_metrics(tags)
