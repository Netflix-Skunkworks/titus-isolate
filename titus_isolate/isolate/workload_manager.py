import copy
import json
from threading import Lock
import time
from typing import List, Dict

from titus_isolate import log

from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.constants import *
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.workload_allocate_response import WorkloadAllocateResponse
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.config.constants import EC2_INSTANCE_ID
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.metrics_utils import *
from titus_isolate.metrics.constants import *
from titus_isolate.metrics.event_log import report_cpu_event
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.utils import visualize_cpu_comparison
from titus_isolate.model.workload_interface import Workload
from titus_isolate.numa.utils import update_numa_balancing
from titus_isolate.utils import get_workload_monitor_manager, get_config_manager


class WorkloadManager(MetricsReporter):

    def __init__(self, cpu: Cpu, cgroup_manager: CgroupManager, cpu_allocator: CpuAllocator):

        self.__reg = None
        self.__tags = None
        self.__lock = Lock()
        self.__instance_id = get_config_manager().get_str(EC2_INSTANCE_ID)

        self.__cpu_allocator = cpu_allocator

        self.__error_count = 0
        self.__added_count = 0
        self.__removed_count = 0
        self.__rebalanced_count = 0
        self.__workload_processing_duration_sec = 0
        self.__update_state_duration_sec = 0

        self.__cpu = cpu
        self.__cgroup_manager = cgroup_manager
        self.__wmm = get_workload_monitor_manager()
        self.__workloads = {}
        self.__last_response = None

        log.info("Created workload manager")

    def add_workload(self, workload):
        update_numa_balancing(workload, self.__cpu)

        succeeded = self.__update_workload(self.__add_workload, workload, workload.get_id())
        if succeeded:
            self.__added_count += 1
        else:
            self.__remove_workload(workload.get_id())

    def remove_workload(self, workload_id):
        self.__cgroup_manager.release_container(workload_id)
        self.__update_workload(self.__remove_workload, workload_id, workload_id)
        self.__removed_count += 1

    def rebalance(self):
        succeeded = self.__update_workload(self.__rebalance, None, None)
        if succeeded:
            self.__rebalanced_count += 1

    @staticmethod
    def __get_workload_processing_metric_name(func_name: str) -> str:
        return "titus-isolate.{}.workloadProcessingDurationSec".format(func_name)

    def __update_workload(self, func, arg, workload_id):
        try:
            with self.__lock:
                log.debug("Acquired lock for func: {} on workload: {}".format(func.__name__, workload_id))
                start_time = time.time()
                func(arg)
                stop_time = time.time()
                if self.__reg is not None:
                    self.__reg.distribution_summary(self.__get_workload_processing_metric_name(func.__name__), self.__tags).record(stop_time - start_time)
                    self.__reg.distribution_summary(WORKLOAD_PROCESSING_DURATION, self.__tags).record(stop_time - start_time)

            log.debug("Released lock for func: {} on workload: {}".format(func.__name__, workload_id))
            return True
        except Exception:
            self.__error_count += 1
            log.error("Failed to execute func: {} on workload: {}".format(func.__name__, workload_id))
            return False

    def __add_workload(self, workload):
        log.info("Assigning '{}' thread(s) to workload: '{}'".format(workload.get_thread_count(), workload.get_id()))

        workload_map = self.get_workload_map_copy()
        workload_map[workload.get_id()] = workload

        request = self.__get_threads_request(workload.get_id(), workload_map, "assign")
        response = self.__cpu_allocator.assign_threads(request)

        self.__update_state(response, workload_map)
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
        self.__update_state(response, workload_map)
        report_cpu_event(request, response)

    def __rebalance(self, dummy):
        request = self.__get_rebalance_request()
        response = self.__cpu_allocator.rebalance(request)

        self.__update_state(response, request.get_workloads())
        report_cpu_event(request, response)

    def __update_state(self, response: AllocateResponse, new_workloads):
        start_time = time.time()
        old_cpu = self.get_cpu_copy()
        new_cpu = response.get_cpu()

        self.__apply_isolation(response)
        self.__cpu = new_cpu
        self.__workloads = new_workloads
        self.__last_response = response

        if old_cpu != new_cpu:
            self.__report_cpu_state(old_cpu, new_cpu)

        stop_time = time.time()
        if self.__reg is not None:
            self.__reg.distribution_summary(UPDATE_STATE_DURATION, self.__tags).record(stop_time - start_time)

    def __apply_isolation(self, response: AllocateResponse):
        last_w_responses = self.__get_workload_allocation_dict(self.__last_response)

        for w_alloc in response.get_workload_allocations():
            last_w_alloc = last_w_responses.get(w_alloc.get_workload_id(), None)
            if w_alloc == last_w_alloc:
                log.info("Skipping update of workload: {}".format(w_alloc.get_workload_id()))
                continue

            workload_id = w_alloc.get_workload_id()
            thread_ids = w_alloc.get_thread_ids()
            quota = w_alloc.get_cpu_quota()
            shares = w_alloc.get_cpu_shares()
            memory_migrate = w_alloc.get_memory_migrate()
            memory_spread_page = w_alloc.get_memory_spread_page()
            memory_spread_slab = w_alloc.get_memory_spread_slab()

            log.info(f'updating workload: {workload_id} '
                     f'cpuset: {thread_ids}, '
                     f'quota: {quota}, '
                     f'shares: {shares}, '
                     f'memory_migrate: {memory_migrate}, '
                     f'memory_spread_page: {memory_spread_page}, '
                     f'memory_spread_slab: {memory_spread_slab}')

            # This ordering is important for reporting whether a workload is isolated.
            # We must always set the "cpuset" first.
            self.__cgroup_manager.set_cpuset(workload_id, thread_ids)
            self.__cgroup_manager.set_quota(workload_id, quota)
            self.__cgroup_manager.set_shares(workload_id, shares)
            self.__cgroup_manager.set_memory_migrate(workload_id, memory_migrate)
            self.__cgroup_manager.set_memory_spread_page(workload_id, memory_spread_page)
            self.__cgroup_manager.set_memory_spread_slab(workload_id, memory_spread_slab)

    @staticmethod
    def __get_workload_allocation_dict(response: AllocateResponse) -> Dict[str, WorkloadAllocateResponse]:
        w_responses = {}

        if response is None:
            return w_responses

        for w_alloc in response.get_workload_allocations():
            w_responses[w_alloc.get_workload_id()] = w_alloc

        return w_responses

    def __get_request_metadata(self, request_type) -> dict:
        config_manager = get_config_manager()
        return {
            "type": request_type,
            "instance_id": self.__instance_id,
            "region": config_manager.get_region(),
            "environment": config_manager.get_environment()
        }

    @staticmethod
    def __get_optional_default(func, default):
        opt = func()
        if opt is None:
            return default
        return opt

    def __get_threads_request(self, workload_id, workload_map, request_type):
        resource_usage = self.__wmm.get_resource_usage(workload_map.keys())
        log.debug("resource_usage: %s", json.dumps(resource_usage.serialize()))
        cpu_usage = self.__get_optional_default(resource_usage.get_cpu_usage, {})
        mem_usage = self.__get_optional_default(resource_usage.get_mem_usage, {})
        net_recv_usage = self.__get_optional_default(resource_usage.get_net_recv_usage, {})
        net_trans_usage = self.__get_optional_default(resource_usage.get_net_trans_usage, {})
        disk_usage = self.__get_optional_default(resource_usage.get_disk_usage, {})

        return AllocateThreadsRequest(
            cpu=self.get_cpu_copy(),
            workload_id=workload_id,
            workloads=workload_map,
            resource_usage=resource_usage,
            cpu_usage=cpu_usage,
            mem_usage=mem_usage,
            net_recv_usage=net_recv_usage,
            net_trans_usage=net_trans_usage,
            disk_usage=disk_usage,
            metadata=self.__get_request_metadata(request_type))

    def __get_rebalance_request(self):
        workload_map = self.get_workload_map_copy()
        resource_usage = self.__wmm.get_resource_usage(workload_map.keys())
        log.debug("resource_usage: %s", json.dumps(resource_usage.serialize()))
        cpu_usage = self.__get_optional_default(resource_usage.get_cpu_usage, {})
        mem_usage = self.__get_optional_default(resource_usage.get_mem_usage, {})
        net_recv_usage = self.__get_optional_default(resource_usage.get_net_recv_usage, {})
        net_trans_usage = self.__get_optional_default(resource_usage.get_net_trans_usage, {})
        disk_usage = self.__get_optional_default(resource_usage.get_disk_usage, {})

        return AllocateRequest(
            cpu=self.get_cpu_copy(),
            workloads=workload_map,
            resource_usage=resource_usage,
            cpu_usage=cpu_usage,
            mem_usage=mem_usage,
            net_recv_usage=net_recv_usage,
            net_trans_usage=net_trans_usage,
            disk_usage=disk_usage,
            metadata=self.__get_request_metadata("rebalance"))

    def get_workloads(self) -> List[Workload]:
        return list(self.__workloads.values())

    def get_workload_map_copy(self):
        return copy.deepcopy(self.__workloads)

    def get_isolated_workload_ids(self):
        return self.__cgroup_manager.get_isolated_workload_ids()

    def is_isolated(self, workload_id):
        if isinstance(self.__cpu_allocator, NoopCpuAllocator):
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

    def get_allocator_name(self):
        return self.__cpu_allocator.get_name()

    @staticmethod
    def __report_cpu_state(old_cpu, new_cpu):
        log.info(visualize_cpu_comparison(old_cpu, new_cpu))

    @staticmethod
    def __get_free_thread_count(response: AllocateResponse):
        if response is None:
            return 0

        free_thread_ids = response.get_metadata().get(FREE_THREAD_IDS, [])
        return len(free_thread_ids)

    @staticmethod
    def __get_oversubscribable_thread_count(response: AllocateResponse):
        if response is None:
            return 0

        oversubscribable_thread_count = 0
        free_thread_ids = response.get_metadata().get(FREE_THREAD_IDS, [])

        for t in response.get_cpu().get_threads():
            if t.get_id() in free_thread_ids and len(t.get_workload_ids()) > 0:
                oversubscribable_thread_count += 1

        return oversubscribable_thread_count

    def set_registry(self, registry, tags):
        self.__reg = registry
        self.__tags = tags
        self.__cpu_allocator.set_registry(registry, tags)
        self.__cgroup_manager.set_registry(registry, tags)

    def report_metrics(self, tags):
        cpu = self.get_cpu_copy()

        self.__reg.gauge(RUNNING, tags).set(1)
        self.__reg.gauge(WORKLOAD_COUNT_KEY, tags).set(len(self.get_workloads()))

        self.__reg.counter(ADDED_KEY, tags).increment(self.get_added_count())
        self.__reg.counter(REMOVED_KEY, tags).increment(self.get_removed_count())
        self.__reg.counter(REBALANCED_KEY, tags).increment(self.get_rebalanced_count())
        self.__reg.counter(SUCCEEDED_KEY, tags).increment(self.get_success_count())
        self.__reg.counter(FAILED_KEY, tags).increment(self.get_error_count())

        self.__added_count = 0
        self.__removed_count = 0
        self.__rebalanced_count = 0
        self.__error_count = 0

        cross_package_violation_count = len(get_cross_package_violations(cpu))
        shared_core_violation_count = len(get_shared_core_violations(cpu))
        self.__reg.gauge(PACKAGE_VIOLATIONS_KEY, tags).set(cross_package_violation_count)
        self.__reg.gauge(CORE_VIOLATIONS_KEY, tags).set(shared_core_violation_count)

        # Allocation / Request sizes
        self.__reg.gauge(ALLOCATED_SIZE_KEY, tags).set(get_allocated_size(cpu))
        self.__reg.gauge(UNALLOCATED_SIZE_KEY, tags).set(get_unallocated_size(cpu))
        self.__reg.gauge(OVERSUBSCRIBED_THREADS_KEY, tags).set(get_oversubscribed_thread_count(cpu))
        self.__reg.gauge(BURSTABLE_THREADS_KEY, tags).set(self.__get_free_thread_count(self.__last_response))
        self.__reg.gauge(OVERSUBSCRIBABLE_THREADS_KEY, tags).set(self.__get_oversubscribable_thread_count(self.__last_response))

        # Have the sub-components report metrics
        self.__cpu_allocator.report_metrics(tags)
        self.__cgroup_manager.report_metrics(tags)
