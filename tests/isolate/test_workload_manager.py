import logging
import unittest
import uuid

from spectator import Registry

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, TestContext, gauge_value_equals, gauge_value_reached, get_threads_with_workload
from titus_isolate import log
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.isolate.detect import get_cross_package_violations
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import RUNNING, ADDED_KEY, REMOVED_KEY, SUCCEEDED_KEY, FAILED_KEY, \
    WORKLOAD_COUNT_KEY, PACKAGE_VIOLATIONS_KEY, CORE_VIOLATIONS_KEY, \
    IP_ALLOCATOR_TIMEBOUND_COUNT, ALLOCATOR_CALL_DURATION, FULL_CORES_KEY, HALF_CORES_KEY, \
    EMPTY_CORES_KEY
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT, is_cpu_full
from titus_isolate.model.workload import Workload
from titus_isolate.utils import set_config_manager

config_logs(logging.DEBUG)
set_config_manager(ConfigManager(TestPropertyProvider({})))

ALLOCATORS = [IntegerProgramCpuAllocator(), GreedyCpuAllocator()]


class TestWorkloadManager(unittest.TestCase):

    def test_single_static_workload_lifecycle(self):
        for allocator in ALLOCATORS:
            thread_count = 2
            workload = Workload(uuid.uuid4(), thread_count, STATIC)

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
            thread_count = 2
            workload = Workload(uuid.uuid4(), thread_count, BURST)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)

            # Add workload
            workload_manager.add_workload(workload)
            self.assertEqual(1, cgroup_manager.container_update_counts[workload.get_id()])

            # All threads should have been assigned to the only burst workload.
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cgroup_manager.container_update_map[workload.get_id()]))

            # All threads should have been consumed from the cpu model perspective.
            self.assertEqual(0, len(workload_manager.get_cpu().get_empty_threads()))

            # Remove workload
            workload_manager.remove_workload(workload.get_id())
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_remove_unknown_workload(self):
        for allocator in ALLOCATORS:
            unknown_workload_id = "unknown"
            thread_count = 2
            workload = Workload(uuid.uuid4(), thread_count, STATIC)

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

    def __assert_container_update_counts(self, cgroup_manager, workloads, counts):
        self.assertEqual(len(workloads), len(counts))
        for i in range(len(workloads)):
            self.assertEqual(counts[i], cgroup_manager.container_update_counts[workloads[i].get_id()])

    def __get_expected_burst_thread_count(self, cpu, workloads):
        expected_burst_count = len(cpu.get_threads())
        for w in workloads:
            if w.get_type() == STATIC:
                expected_burst_count -= w.get_thread_count()
        return expected_burst_count

    def __assert_container_thread_count(self, cpu, cgroup_manager, workloads):
        expected_burst_count = self.__get_expected_burst_thread_count(cpu, workloads)

        for w in workloads:
            if w.get_type() == STATIC:
                self.assertEqual(
                    w.get_thread_count(),
                    len(cgroup_manager.container_update_map[w.get_id()]))
            else:
                self.assertEqual(
                    expected_burst_count,
                    len(cgroup_manager.container_update_map[w.get_id()]))

    def __assert_cpu_thread_count(self, cpu, workloads):
        expected_burst_count = self.__get_expected_burst_thread_count(cpu, workloads)

        for w in workloads:
            if w.get_type() == STATIC:
                self.assertEqual(
                    w.get_thread_count(),
                    len(get_threads_with_workload(cpu, w.get_id())))
            else:
                self.assertEqual(
                    expected_burst_count,
                    len(get_threads_with_workload(cpu, w.get_id())))

    def test_alternating_static_burst_workloads(self):
        for allocator in ALLOCATORS:
            thread_count = 2

            burst0 = Workload("burst0", thread_count, BURST)
            burst1 = Workload("burst1", thread_count, BURST)
            static0 = Workload("static0", thread_count, STATIC)
            static1 = Workload("static1", thread_count, STATIC)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)

            # Add static workload
            log.info("ADDING STATIC0")
            workload_manager.add_workload(static0)
            self.__assert_container_update_counts(cgroup_manager, [static0], [1])
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0])

            # Add burst workload
            log.info("ADDING BURST0")
            workload_manager.add_workload(burst0)
            self.__assert_container_update_counts(cgroup_manager, [static0, burst0], [1, 1])
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0, burst0])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0, burst0])

            # Add static workload
            log.info("ADDING STATIC1")
            workload_manager.add_workload(static1)
            self.__assert_container_update_counts(cgroup_manager, [static0, burst0, static1], [1, 2, 1])
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0, burst0, static1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0, burst0, static1])

            # Add burst workload
            log.info("ADDING BURST1")
            workload_manager.add_workload(burst1)
            self.__assert_container_update_counts(cgroup_manager, [static0, burst0, static1, burst1], [1, 2, 1, 1])
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [static0, burst0, static1, burst1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [static0, burst0, static1, burst1])

            # Remove static workload
            log.info("REMOVING STATIC0")
            workload_manager.remove_workload(static0.get_id())
            self.__assert_container_update_counts(cgroup_manager, [burst0, static1, burst1], [3, 1, 2])
            self.__assert_container_thread_count(workload_manager.get_cpu(), cgroup_manager, [burst0, static1, burst1])
            self.__assert_cpu_thread_count(workload_manager.get_cpu(), [burst0, static1, burst1])

    def test_no_cross_packages_placement_no_bad_affinity_ip(self):
        w_a = Workload("a", 3, STATIC)
        w_b = Workload("b", 2, STATIC)
        w_c = Workload("c", 1, STATIC)
        w_d = Workload("d", 2, STATIC)

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
        self.assertTrue(gauge_value_equals(registry, FULL_CORES_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, HALF_CORES_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EMPTY_CORES_KEY, len(test_context.get_cpu().get_cores())))

    def test_add_metrics(self):
        test_context = TestContext()
        registry = Registry()
        reporter = test_context.get_workload_manager()
        reporter.set_registry(registry)

        reporter.add_workload(Workload(uuid.uuid4(), 2, STATIC))
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
        self.assertTrue(gauge_value_equals(registry, FULL_CORES_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, HALF_CORES_KEY, 2))
        self.assertTrue(gauge_value_equals(registry, EMPTY_CORES_KEY, 6))

    def test_edge_case_ip_allocator_metrics(self):
        # This is a specific scenario causing troubles to the solver.
        # We should hit the time-bound limit and report it.

        registry = Registry()

        cpu = get_cpu(2, 16, 2)
        allocator = IntegerProgramCpuAllocator(solver_max_runtime_secs=0.01)
        test_context = TestContext(cpu, allocator)

        workload_manager = test_context.get_workload_manager()
        workload_manager.set_registry(registry)
        cnt_evts = 0

        for i in range(15):
            workload_manager.add_workload(Workload(str(i), 2, STATIC))
        cnt_evts += 15

        workload_manager.add_workload(Workload("15", 1, STATIC))
        cnt_evts += 1

        for i in range(9):
            workload_manager.add_workload(Workload(str(i+cnt_evts), 2, STATIC))

        workload_manager.remove_workload("15")
        workload_manager.report_metrics({})

        self.assertTrue(gauge_value_reached(registry, IP_ALLOCATOR_TIMEBOUND_COUNT, 1))
        self.assertTrue(gauge_value_reached(registry, ALLOCATOR_CALL_DURATION, 0.1))

    def test_assign_to_full_cpu_fails(self):
        for allocator in ALLOCATORS:
            # Fill the CPU
            w0 = Workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)

            cgroup_manager = MockCgroupManager()
            workload_manager = WorkloadManager(get_cpu(), cgroup_manager, allocator)
            workload_manager.add_workload(w0)

            self.assertTrue(is_cpu_full(workload_manager.get_cpu()))

            # Fail to claim one more thread
            error_count = workload_manager.get_error_count()
            w1 = Workload(uuid.uuid4(), 1, STATIC)
            workload_manager.add_workload(w1)
            self.assertEqual(error_count + 1, workload_manager.get_error_count())

    def test_is_isolated(self):
        real_allocators = [GreedyCpuAllocator(), IntegerProgramCpuAllocator()]
        for allocator in real_allocators:
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            self.assertFalse(wm.is_isolated(uuid.uuid4()))

        for allocator in real_allocators:
            workload = Workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            wm.add_workload(workload)
            self.assertTrue(wm.is_isolated(workload.get_id()))

        noop_allocators = [NoopCpuAllocator(), NoopResetCpuAllocator()]
        for allocator in noop_allocators:
            wm = WorkloadManager(get_cpu(), MockCgroupManager(), allocator)
            self.assertTrue(wm.is_isolated(uuid.uuid4()))
