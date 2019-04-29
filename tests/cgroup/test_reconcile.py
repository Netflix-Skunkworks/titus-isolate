import unittest
from unittest.mock import MagicMock

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.test_exit_handler import TestExitHandler
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.constants import RECONCILIATION_FAILURE_EXIT
from titus_isolate.isolate.reconciler import Reconciler
from titus_isolate.model.processor.config import get_cpu

EXIT_HANDLER = TestExitHandler()


class TestUtils(unittest.TestCase):

    def setUp(self):
        global EXIT_HANDLER
        EXIT_HANDLER = TestExitHandler()

    def test_get_workloads(self):
        reconciler = Reconciler(MockCgroupManager(), None)
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
        cpu = get_cpu()

        reconciler = Reconciler(MockCgroupManager(), EXIT_HANDLER)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            EXIT_HANDLER,
            exit_code=None,
            expected_success_count=1,
            expected_skip_count=0)

    def test_reconcile_unisolated_workload(self):
        # Simulate a workload which has been added but which isn't isolated yet
        cpu = get_cpu()
        cpu.get_threads()[0].claim("a")

        cgroup_manager = CgroupManager()
        cgroup_manager.has_pending_work = MagicMock(return_value=True)

        reconciler = Reconciler(cgroup_manager, EXIT_HANDLER)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            EXIT_HANDLER,
            exit_code=None,
            expected_success_count=0,
            expected_skip_count=1)

    def test_reconcile_missing_cpuset(self):
        cpu = get_cpu()
        workload_id = "a"
        cpu.get_threads()[0].claim(workload_id)

        cgroup_manager = CgroupManager()
        cgroup_manager.get_cpuset = MagicMock(return_value=[])

        reconciler = Reconciler(cgroup_manager, EXIT_HANDLER)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            EXIT_HANDLER,
            exit_code=RECONCILIATION_FAILURE_EXIT,
            expected_success_count=1,  # The mock exit handler doesn't actually kill anything, so we get a false success
            expected_skip_count=0)

    def test_reconcile_cpuset_mismatch(self):
        cpu = get_cpu()
        workload_id = "a"
        cpu.get_threads()[0].claim(workload_id)

        cgroup_manager = CgroupManager()
        cgroup_manager.get_isolated_workload_ids = MagicMock(return_value=[workload_id])
        cgroup_manager.get_cpuset = MagicMock(return_value=[42])

        reconciler = Reconciler(cgroup_manager, EXIT_HANDLER)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            EXIT_HANDLER,
            exit_code=RECONCILIATION_FAILURE_EXIT,
            expected_success_count=1,  # The mock exit handler doesn't actually kill anything, so we get a false success
            expected_skip_count=0)

    def test_reconcile_cpuset_match(self):
        cpu = get_cpu()
        workload_id = "a"
        cpu.get_threads()[0].claim(workload_id)

        cgroup_manager = CgroupManager()
        cgroup_manager.get_isolated_workload_ids = MagicMock(return_value=[workload_id])
        cgroup_manager.get_cpuset = MagicMock(return_value=[0])

        reconciler = Reconciler(cgroup_manager, EXIT_HANDLER)
        reconciler.reconcile(cpu)
        self.__validate_state(
            reconciler,
            EXIT_HANDLER,
            exit_code=None,
            expected_success_count=1,
            expected_skip_count=0)

    def __validate_state(self, reconciler, exit_handler, exit_code, expected_success_count, expected_skip_count):
        actual_exit_code = exit_handler.last_code
        self.assertEqual(
            exit_code,
            exit_handler.last_code,
            "Expected exit_code: '{}', found: '{}'".format(exit_code, actual_exit_code))

        actual_success_count = reconciler.get_success_count()
        self.assertEqual(
            expected_success_count,
            actual_success_count,
            "Expected success count: '{}', found: '{}'".format(expected_success_count, actual_success_count))

        actual_skip_count = reconciler.get_skip_count()
        self.assertEqual(
            expected_skip_count,
            actual_skip_count,
            "Expected skip count: '{}', found: '{}'".format(expected_skip_count, actual_skip_count))

