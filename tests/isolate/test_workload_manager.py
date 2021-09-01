import logging
import unittest
import uuid

from spectator import Registry

from tests.allocate.test_allocate import TestWorkloadMonitorManager
from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, TestContext, gauge_value_equals, get_threads_with_workload, \
    get_test_workload, counter_value_equals
from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import TITUS_ISOLATE_MEMORY_MIGRATE, \
    TITUS_ISOLATE_MEMORY_SPREAD_PAGE, TITUS_ISOLATE_MEMORY_SPREAD_SLAB
from titus_isolate.event.constants import STATIC, BURST
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import RUNNING, ADDED_KEY, REMOVED_KEY, SUCCEEDED_KEY, FAILED_KEY, \
    WORKLOAD_COUNT_KEY, PACKAGE_VIOLATIONS_KEY, CORE_VIOLATIONS_KEY, OVERSUBSCRIBED_THREADS_KEY, \
    STATIC_ALLOCATED_SIZE_KEY, BURST_ALLOCATED_SIZE_KEY,  BURST_REQUESTED_SIZE_KEY, ALLOCATED_SIZE_KEY, \
    UNALLOCATED_SIZE_KEY
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT, is_cpu_full
from titus_isolate.utils import set_config_manager, set_workload_monitor_manager

config_logs(logging.DEBUG)
set_config_manager(ConfigManager(TestPropertyProvider({})))
set_workload_monitor_manager(TestWorkloadMonitorManager())

LEGACY_ALLOCATORS = [GreedyCpuAllocator()]
OVERSUBSCRIBING_ALLOCATORS = [NaiveCpuAllocator()]
ALLOCATORS = LEGACY_ALLOCATORS + OVERSUBSCRIBING_ALLOCATORS


class TestWorkloadManager(unittest.TestCase):

    def test_single_static_workload_lifecycle(self):
        for allocator in ALLOCATORS:
            thread_count = 2
            workload = get_test_workload(uuid.uuid4(), thread_count, STATIC)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)

            # Add workload
            workload_manager.add_workload(workload)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))
            self.assertEqual(1, cgroup_manager.container_update_counts[workload.get_id()])

            # Remove workload
            workload_manager.remove_workload(workload.get_id())
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_remove_unknown_workload(self):
        for allocator in ALLOCATORS:
            unknown_workload_id = "unknown"
            thread_count = 2
            workload = get_test_workload(uuid.uuid4(), thread_count, STATIC)

            workload_manager = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)

            # Remove from empty set
            workload_manager.remove_workload(unknown_workload_id)

            # Add workload
            workload_manager.add_workload(workload)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

            # Removal of an unknown workload should have no effect
            workload_manager.remove_workload(unknown_workload_id)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

            # Remove workload with unknown workload, real workload should be removed
            workload_manager.remove_workload(unknown_workload_id)
            workload_manager.remove_workload(workload.get_id())
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def __assert_container_thread_count(self, cpu, cgroup_manager, workloads):
        for w in workloads:
            if w.get_type() == STATIC:
                self.assertEqual(
                    w.get_thread_count(),
                    len(cgroup_manager.container_update_map[w.get_id()]))
            else:
                self.assertTrue(len(cgroup_manager.container_update_map[w.get_id()]) > w.get_thread_count())

    def __assert_cpu_thread_count(self, cpu, workloads):
        for w in workloads:
            if w.get_type() == STATIC:
                self.assertEqual(
                    w.get_thread_count(),
                    len(get_threads_with_workload(cpu, w.get_id())))
            else:
                self.assertTrue(len(get_threads_with_workload(cpu, w.get_id())) > w.get_thread_count())

    def test_empty_metrics(self):
        test_context = TestContext()
        registry = Registry()
        reporter = test_context.get_workload_manager()
        reporter.set_registry(registry, {})
        reporter.report_metrics({})

        self.assertTrue(gauge_value_equals(registry, RUNNING, 1))
        self.assertTrue(counter_value_equals(registry, ADDED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, REMOVED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, SUCCEEDED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, CORE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, ALLOCATED_SIZE_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, UNALLOCATED_SIZE_KEY, len(test_context.get_cpu().get_threads())))

    def test_add_metrics(self):
        test_context = TestContext()
        registry = Registry()
        reporter = test_context.get_workload_manager()
        reporter.set_registry(registry, {})

        workload = get_test_workload(uuid.uuid4(), 2, STATIC)
        reporter.add_workload(workload)
        reporter.report_metrics({})

        self.assertTrue(gauge_value_equals(registry, RUNNING, 1))
        self.assertTrue(counter_value_equals(registry, ADDED_KEY, 1))
        self.assertTrue(counter_value_equals(registry, REMOVED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, SUCCEEDED_KEY, 1))
        self.assertTrue(counter_value_equals(registry, FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 1))
        self.assertTrue(gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, CORE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, ALLOCATED_SIZE_KEY, workload.get_thread_count()))

        expected_unallocated_size = len(test_context.get_cpu().get_threads()) - workload.get_thread_count()
        self.assertTrue(gauge_value_equals(registry, UNALLOCATED_SIZE_KEY, expected_unallocated_size))

    def test_assign_to_full_cpu_fails(self):
        for allocator in LEGACY_ALLOCATORS:
            # Fill the CPU
            w0 = get_test_workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)
            workload_manager.add_workload(w0)

            self.assertTrue(is_cpu_full(workload_manager.get_cpu()))

            # Fail to claim one more thread
            error_count = workload_manager.get_error_count()
            w1 = get_test_workload(uuid.uuid4(), 1, STATIC)
            workload_manager.add_workload(w1)
            self.assertEqual(error_count + 1, workload_manager.get_error_count())

    def test_is_isolated(self):
        real_allocators = [GreedyCpuAllocator(), NaiveCpuAllocator()]
        for allocator in real_allocators:
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            self.assertFalse(wm.is_isolated(uuid.uuid4()))

        for allocator in real_allocators:
            workload = get_test_workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            wm.add_workload(workload)
            self.assertTrue(wm.is_isolated(workload.get_id()))

        wm = WorkloadManager(get_cpu(), MockCgroupManager(), NoopCpuAllocator())
        self.assertTrue(wm.is_isolated(uuid.uuid4()))

    def test_thread_allocation_computation(self):
        for allocator in [NaiveCpuAllocator(), GreedyCpuAllocator()]:
            static_thread_count = 2
            w_static = get_test_workload("s", static_thread_count, STATIC)

            cgroup_manager = MockCgroupManager()
            registry = Registry()

            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)
            workload_manager.set_registry(registry, {})
            workload_manager.add_workload(w_static)

            workload_manager.report_metrics({})
            total_thread_count = len(workload_manager.get_cpu().get_threads())
            self.assertTrue(gauge_value_equals(registry, ALLOCATED_SIZE_KEY, w_static.get_thread_count()))
            self.assertTrue(gauge_value_equals(registry, UNALLOCATED_SIZE_KEY, total_thread_count - w_static.get_thread_count()))
            self.assertTrue(gauge_value_equals(registry, STATIC_ALLOCATED_SIZE_KEY, static_thread_count))
            self.assertTrue(gauge_value_equals(registry, OVERSUBSCRIBED_THREADS_KEY, 0))

    def test_single_workload_memory_settings(self):
        for allocator in ALLOCATORS:
            thread_count = 2
            workload = get_test_workload(uuid.uuid4(), thread_count, STATIC)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)

            # With an empty configuration we should expect default False behavior
            # for all memory flags
            set_config_manager(ConfigManager(TestPropertyProvider({})))

            workload_manager.add_workload(workload)
            self.assertFalse(cgroup_manager.get_memory_migrate(workload.get_id()))
            self.assertFalse(cgroup_manager.get_memory_spread_page(workload.get_id()))
            self.assertFalse(cgroup_manager.get_memory_spread_slab(workload.get_id()))
            workload_manager.remove_workload(workload.get_id())

            # With all memory configuration options set to True we should expect all memory
            # flags to be set to True
            set_config_manager(ConfigManager(TestPropertyProvider({
                TITUS_ISOLATE_MEMORY_MIGRATE: True,
                TITUS_ISOLATE_MEMORY_SPREAD_PAGE: True,
                TITUS_ISOLATE_MEMORY_SPREAD_SLAB: True,
            })))

            workload_manager.add_workload(workload)
            self.assertTrue(cgroup_manager.get_memory_migrate(workload.get_id()))
            self.assertTrue(cgroup_manager.get_memory_spread_page(workload.get_id()))
            self.assertTrue(cgroup_manager.get_memory_spread_slab(workload.get_id()))
            workload_manager.remove_workload(workload.get_id())

