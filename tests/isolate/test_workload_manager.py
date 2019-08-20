import logging
import unittest
import uuid

from spectator import Registry

from tests.allocate.test_allocate import TestWorkloadMonitorManager, TestCpuUsagePredictorManager
from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, TestContext, gauge_value_equals, get_threads_with_workload, \
    get_test_workload
from titus_isolate import log
from titus_isolate.allocate.forecast_ip_cpu_allocator import ForecastIPCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import DEFAULT_TOTAL_THRESHOLD
from titus_isolate.event.constants import STATIC, BURST
from titus_isolate.isolate.detect import get_cross_package_violations
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import RUNNING, ADDED_KEY, REMOVED_KEY, SUCCEEDED_KEY, FAILED_KEY, \
    WORKLOAD_COUNT_KEY, PACKAGE_VIOLATIONS_KEY, CORE_VIOLATIONS_KEY, IP_ALLOCATOR_TIMEBOUND_COUNT, \
    OVERSUBSCRIBED_THREADS_KEY, STATIC_ALLOCATED_SIZE_KEY, BURST_ALLOCATED_SIZE_KEY, \
    BURST_REQUESTED_SIZE_KEY, ALLOCATED_SIZE_KEY, UNALLOCATED_SIZE_KEY
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT, is_cpu_full
from titus_isolate.monitor.oversubscribe_free_thread_provider import OversubscribeFreeThreadProvider
from titus_isolate.utils import set_config_manager, set_workload_monitor_manager

config_logs(logging.DEBUG)
set_config_manager(ConfigManager(TestPropertyProvider({})))
set_workload_monitor_manager(TestWorkloadMonitorManager())

forecast_ip_alloc_simple = ForecastIPCpuAllocator(
    TestCpuUsagePredictorManager(),
    ConfigManager(TestPropertyProvider({})),
    OversubscribeFreeThreadProvider(DEFAULT_TOTAL_THRESHOLD))

LEGACY_ALLOCATORS = [IntegerProgramCpuAllocator(), GreedyCpuAllocator()]
OVERSUBSCRIBING_ALLOCATORS = [forecast_ip_alloc_simple]
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

    def test_single_burst_workload_lifecycle(self):
        for allocator in ALLOCATORS:
            requested_thread_count = 2
            workload = get_test_workload(uuid.uuid4(), requested_thread_count, BURST)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)

            # Add workload
            workload_manager.add_workload(workload)
            self.assertEqual(1, cgroup_manager.container_update_counts[workload.get_id()])

            # More than the requested threads should have been assigned to the only burst workload.
            self.assertTrue(len(cgroup_manager.container_update_map[workload.get_id()]) > requested_thread_count)

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

    def test_alternating_static_burst_workloads(self):
        for allocator in ALLOCATORS:
            thread_count = 2

            burst0 = get_test_workload("burst0", thread_count, BURST)
            burst1 = get_test_workload("burst1", thread_count, BURST)
            static0 = get_test_workload("static0", thread_count, STATIC)
            static1 = get_test_workload("static1", thread_count, STATIC)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)

            # Add static workload
            log.info("ADDING STATIC0")
            workload_manager.add_workload(static0)
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0])

            # Add burst workload
            log.info("ADDING BURST0")
            workload_manager.add_workload(burst0)
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0, burst0])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0, burst0])

            # Add static workload
            log.info("ADDING STATIC1")
            workload_manager.add_workload(static1)
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0, burst0, static1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0, burst0, static1])

            # Add burst workload
            log.info("ADDING BURST1")
            workload_manager.add_workload(burst1)
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0, burst0, static1, burst1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0, burst0, static1, burst1])

            # Remove static workload
            log.info("REMOVING STATIC0")
            workload_manager.remove_workload(static0.get_id())
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [burst0, static1, burst1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [burst0, static1, burst1])

            # Remove static workload
            log.info("REMOVING BURST0")
            workload_manager.remove_workload(burst0.get_id())
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static1, burst1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static1, burst1])

    def test_no_cross_packages_placement_no_bad_affinity_ip(self):
        w_a = get_test_workload("a", 3, STATIC)
        w_b = get_test_workload("b", 2, STATIC)
        w_c = get_test_workload("c", 1, STATIC)
        w_d = get_test_workload("d", 2, STATIC)

        cpu = get_cpu(package_count=2, cores_per_package=2, threads_per_core=2)

        workload_manager = WorkloadManager(cpu, MockCgroupManager(), IntegerProgramCpuAllocator())
        workload_manager.add_workload(w_a)
        workload_manager.add_workload(w_b)
        workload_manager.add_workload(w_c)
        workload_manager.add_workload(w_d)

        self.assertEqual(0, len(get_cross_package_violations(workload_manager.get_cpu())))
        self.assertEqual(0, len(workload_manager.get_cpu().get_empty_threads()))

    def test_empty_metrics(self):
        test_context = TestContext()
        registry = Registry()
        reporter = test_context.get_workload_manager()
        reporter.set_registry(registry)
        reporter.report_metrics({})

        self.assertTrue(gauge_value_equals(registry, RUNNING, 1))
        self.assertTrue(gauge_value_equals(registry, ADDED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, REMOVED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, SUCCEEDED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, CORE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, IP_ALLOCATOR_TIMEBOUND_COUNT, 0))
        self.assertTrue(gauge_value_equals(registry, ALLOCATED_SIZE_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, UNALLOCATED_SIZE_KEY, len(test_context.get_cpu().get_threads())))

    def test_add_metrics(self):
        test_context = TestContext()
        registry = Registry()
        reporter = test_context.get_workload_manager()
        reporter.set_registry(registry)

        workload = get_test_workload(uuid.uuid4(), 2, STATIC)
        reporter.add_workload(workload)
        reporter.report_metrics({})

        self.assertTrue(gauge_value_equals(registry, RUNNING, 1))
        self.assertTrue(gauge_value_equals(registry, ADDED_KEY, 1))
        self.assertTrue(gauge_value_equals(registry, REMOVED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, SUCCEEDED_KEY, 1))
        self.assertTrue(gauge_value_equals(registry, FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 1))
        self.assertTrue(gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, CORE_VIOLATIONS_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, IP_ALLOCATOR_TIMEBOUND_COUNT, 0))
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
        real_allocators = [GreedyCpuAllocator(), IntegerProgramCpuAllocator()]
        for allocator in real_allocators:
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            self.assertFalse(wm.is_isolated(uuid.uuid4()))

        for allocator in real_allocators:
            workload = get_test_workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            wm.add_workload(workload)
            self.assertTrue(wm.is_isolated(workload.get_id()))

        noop_allocators = [NoopCpuAllocator(), NoopResetCpuAllocator()]
        for allocator in noop_allocators:
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            self.assertTrue(wm.is_isolated(uuid.uuid4()))

    def test_thread_allocation_computation(self):
        for allocator in [IntegerProgramCpuAllocator(), GreedyCpuAllocator()]:
            static_thread_count = 2
            burst_thread_count = 4
            w_static = get_test_workload("s", static_thread_count, STATIC)
            w_burst = get_test_workload("b", burst_thread_count, BURST)

            cgroup_manager = MockCgroupManager()
            registry = Registry()

            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)
            workload_manager.set_registry(registry)
            workload_manager.add_workload(w_static)
            workload_manager.add_workload(w_burst)

            workload_manager.report_metrics({})
            total_thread_count = len(workload_manager.get_cpu().get_threads())
            expected_burst_allocation_size = total_thread_count - static_thread_count
            self.assertTrue(gauge_value_equals(registry, ALLOCATED_SIZE_KEY, total_thread_count))
            self.assertTrue(gauge_value_equals(registry, UNALLOCATED_SIZE_KEY, 0))
            self.assertTrue(gauge_value_equals(registry, STATIC_ALLOCATED_SIZE_KEY, static_thread_count))
            self.assertTrue(gauge_value_equals(registry, BURST_ALLOCATED_SIZE_KEY, expected_burst_allocation_size))
            self.assertTrue(gauge_value_equals(registry, BURST_REQUESTED_SIZE_KEY, burst_thread_count))
            self.assertTrue(gauge_value_equals(registry, OVERSUBSCRIBED_THREADS_KEY, 0))

            # Claim every thread for the burst workload which will oversubscribe the static threads
            for t in workload_manager.get_cpu().get_threads():
                t.claim(w_burst.get_id())

            workload_manager.report_metrics({})
            self.assertTrue(gauge_value_equals(registry, ALLOCATED_SIZE_KEY, total_thread_count))
            self.assertTrue(gauge_value_equals(registry, UNALLOCATED_SIZE_KEY, 0))
            self.assertTrue(gauge_value_equals(registry, STATIC_ALLOCATED_SIZE_KEY, static_thread_count))
            self.assertTrue(gauge_value_equals(registry, BURST_ALLOCATED_SIZE_KEY, total_thread_count))
            self.assertTrue(gauge_value_equals(registry, BURST_REQUESTED_SIZE_KEY, burst_thread_count))
            self.assertTrue(gauge_value_equals(registry, OVERSUBSCRIBED_THREADS_KEY, static_thread_count))
