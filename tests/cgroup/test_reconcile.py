import unittest
from unittest.mock import MagicMock

from tests.test_exit_handler import TestExitHandler
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.constants import RECONCILIATION_FAILURE_EXIT
from titus_isolate.isolate.reconciler import Reconciler
from titus_isolate.model.processor.config import get_cpu


class TestUtils(unittest.TestCase):

    def test_get_workloads(self):
        reconciler = Reconciler(None, None)
        cpu = get_cpu(1, 4, 1)  # 1 socket, 4 cores, 1 thread per core

        threads = cpu.get_threads()
        threads[0].claim("a")
        threads[0].claim("e")
        threads[1].claim("b")
        threads[1].claim("c")
        threads[1].claim("d")
        threads[2].claim("d")
        threads[2].claim("e")
        threads[3].claim("e")

        workloads = reconciler.get_workloads(cpu)
        self.assertEqual([0], workloads["a"])
        self.assertEqual([1], workloads["b"])
        self.assertEqual([1], workloads["c"])
        self.assertEqual([1, 2], workloads["d"])
        self.assertEqual([0, 2, 3], workloads["e"])

    def test_reconcile_no_workloads(self):
        exit_handler = TestExitHandler()
        cpu = get_cpu()

        reconciler = Reconciler(None, exit_handler)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            exit_handler,
            exit_code=None,
            unisolated_count=0,
            missing_cpuset_count=0)

    def test_reconcile_unisolated_workload(self):
        exit_handler = TestExitHandler()

        # Simulate a workload which has been added but which isn't isolated yet
        cpu = get_cpu()
        cpu.get_threads()[0].claim("a")

        cgroup_manager = CgroupManager()
        cgroup_manager.get_isolated_workload_ids = MagicMock(return_value=[])

        reconciler = Reconciler(cgroup_manager, exit_handler)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            exit_handler,
            exit_code=None,
            unisolated_count=1,
            missing_cpuset_count=0)

    def test_reconcile_missing_cpuset(self):
        exit_handler = TestExitHandler()

        # Simulate a workload which has been added but which isn't isolated yet
        cpu = get_cpu()
        workload_id = "a"
        cpu.get_threads()[0].claim(workload_id)

        cgroup_manager = CgroupManager()
        cgroup_manager.get_isolated_workload_ids = MagicMock(return_value=[workload_id])

        reconciler = Reconciler(cgroup_manager, exit_handler)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            exit_handler,
            exit_code=None,
            unisolated_count=0,
            missing_cpuset_count=1)

    def test_reconcile_cpuset_mismatch(self):
        exit_handler = TestExitHandler()

        # Simulate a workload which has been added but which isn't isolated yet
        cpu = get_cpu()
        workload_id = "a"
        cpu.get_threads()[0].claim(workload_id)

        cgroup_manager = CgroupManager()
        cgroup_manager.get_isolated_workload_ids = MagicMock(return_value=[workload_id])
        cgroup_manager.get_cpuset = MagicMock(return_value=[42])

        reconciler = Reconciler(cgroup_manager, exit_handler)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            exit_handler,
            exit_code=RECONCILIATION_FAILURE_EXIT,
            unisolated_count=0,
            missing_cpuset_count=0)

    def test_reconcile_cpuset_match(self):
        exit_handler = TestExitHandler()

        # Simulate a workload which has been added but which isn't isolated yet
        cpu = get_cpu()
        workload_id = "a"
        cpu.get_threads()[0].claim(workload_id)

        cgroup_manager = CgroupManager()
        cgroup_manager.get_isolated_workload_ids = MagicMock(return_value=[workload_id])
        cgroup_manager.get_cpuset = MagicMock(return_value=[0])

        reconciler = Reconciler(cgroup_manager, exit_handler)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            exit_handler,
            exit_code=None,
            unisolated_count=0,
            missing_cpuset_count=0)

    def __validate_state(self, reconciler, exit_handler, exit_code, unisolated_count, missing_cpuset_count):
        actual_exit_code = exit_handler.last_code
        self.assertEqual(exit_code, exit_handler.last_code, "Expected exit_code: '{}', found: '{}'".format(exit_code, actual_exit_code))

        actual_unisolated_count = reconciler.get_unisolated_workload_count()
        self.assertEqual(unisolated_count, reconciler.get_unisolated_workload_count(), "Expected unisolated_count: '{}', found: '{}'".format(unisolated_count, actual_unisolated_count))

        actual_missing_cpuset_count = reconciler.get_missing_cpuset_count()
        self.assertEqual(missing_cpuset_count, reconciler.get_missing_cpuset_count(), "Expected missing cpuset count: '{}', found: '{}'".format(missing_cpuset_count, actual_missing_cpuset_count))

        expected_total_warning_count = unisolated_count + missing_cpuset_count
        actual_total_warning_count = reconciler.get_total_warning_count()

        self.assertEqual(unisolated_count + missing_cpuset_count, reconciler.get_total_warning_count(), "Expected total warning count: '{}', found: '{}'".format(expected_total_warning_count, actual_total_warning_count))

