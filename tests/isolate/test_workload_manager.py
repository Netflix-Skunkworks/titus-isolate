import logging
import unittest
import uuid

from tests.docker.mock_docker import MockDockerClient, MockContainer
from tests.utils import wait_until
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.cpu import assign_threads
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.utils import get_cpu, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)
log = logging.getLogger()


class TestWorkloadManager(unittest.TestCase):

    def test_single_static_workload_lifecycle(self):
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)

        docker_client = MockDockerClient([MockContainer(workload)])
        workload_manager = WorkloadManager(get_cpu(), docker_client)

        # Add workload
        workload_manager.add_workloads([workload])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_single_burst_workload_lifecycle(self):
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, BURST)

        docker_container = MockContainer(workload)
        docker_client = MockDockerClient([docker_container])
        workload_manager = WorkloadManager(get_cpu(), docker_client)

        # Add workload
        workload_manager.add_workloads([workload])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(docker_container.update_calls) == 1)

        # All threads should have been assigned to the only burst workload.
        update_call = docker_container.update_calls[0]
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(update_call))

        # No threads should have been consumed from the cpu model perspective.
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_alternating_static_burst_workloads(self):
        thread_count = 2

        burst0 = Workload("burst0", thread_count, BURST)
        burst1 = Workload("burst1", thread_count, BURST)
        static0 = Workload("static0", thread_count, STATIC)
        static1 = Workload("static1", thread_count, STATIC)

        burst_container0 = MockContainer(burst0)
        burst_container1 = MockContainer(burst1)
        static_container0 = MockContainer(static0)
        static_container1 = MockContainer(static1)

        docker_client = MockDockerClient([burst_container0, burst_container1, static_container0, static_container1])
        workload_manager = WorkloadManager(get_cpu(), docker_client)

        # Add static workload
        log.info("ADDING STATIC0")
        workload_manager.add_workloads([static0])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(static_container0.update_calls) == 1)
        expected_free_thread_count = DEFAULT_TOTAL_THREAD_COUNT - thread_count
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Add burst workload
        log.info("ADDING BURST0")
        workload_manager.add_workloads([burst0])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(burst_container0.update_calls) == 1)
        # No change in empty threads expected
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Add static workload
        log.info("ADDING STATIC1")
        workload_manager.add_workloads([static1])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(static_container1.update_calls) == 1)
        expected_free_thread_count = expected_free_thread_count - thread_count
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))
        # The burst0 container should be updated again because the burst footprint changed after the addition of a
        # static workload
        wait_until(lambda: len(burst_container0.update_calls) == 2)
        self.assertEqual(expected_free_thread_count, len(burst_container0.update_calls[1]))

        # Add burst workload
        log.info("ADDING BURST1")
        workload_manager.add_workloads([burst1])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(burst_container1.update_calls) == 1)
        # No change in empty threads expected
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove static workload
        log.info("REMOVING STATIC0")
        workload_manager.remove_workloads([static0.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(burst_container0.update_calls) == 3)
        wait_until(lambda: len(burst_container1.update_calls) == 2)
        # Empty threads should have increased
        expected_free_thread_count = expected_free_thread_count + thread_count
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

    def test_remove_unknown_workload(self):
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)

        docker_client = MockDockerClient([MockContainer(workload)])
        workload_manager = WorkloadManager(get_cpu(), docker_client)

        # Remove from empty set
        workload_manager.remove_workloads(["unknown_workload_id"])

        # Add workload
        workload_manager.add_workloads([workload])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Removal of an unknown workload should have no effect
        workload_manager.remove_workloads(["unknown_workload_id"])
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_rebalance_by_forcing_bad_placement(self):
        cpu = get_cpu(package_count=2, cores_per_package=2, threads_per_core=2)

        # Adding workloads in this order should force w3 to be split across packages
        # It should also cause 2 shared core violations
        w_a = Workload("a", 3, STATIC)
        w_b = Workload("b", 2, STATIC)
        w_c = Workload("c", 1, STATIC)
        w_d = Workload("d", 2, STATIC)

        # We can validate this by manually assigning the workloads to the CPU
        assign_threads(cpu, w_a)
        assign_threads(cpu, w_b)
        assign_threads(cpu, w_c)
        assign_threads(cpu, w_d)

        # We expect the CPU to look like this in the naive iterative placement case.
        #
        #     NOTE: "d" is on both packages and is participating in shared core violations
        #
        # package 0
        #     core 0
        #         thread 0 --> a
        #         thread 1 --> a
        #     core 1
        #         thread 0 --> a
        #         thread 1 --> d        <== shared core / cross package violation
        # package 1
        #     core 0
        #         thread 0 --> b
        #         thread 1 --> b
        #     core 1
        #         thread 0 --> c
        #         thread 1 --> d        <== shared core / cross package violation

        self.assertEqual(1, len(get_cross_package_violations(cpu)))
        self.assertEqual(2, len(get_shared_core_violations(cpu)))

        # Now we should verify that adding these same workloads incrementally to the workload manager actually
        # re-balances workloads to improve upon the poor placement from above.
        cpu = get_cpu(package_count=2, cores_per_package=2, threads_per_core=2)

        docker_client = MockDockerClient(
            [
                MockContainer(w_a),
                MockContainer(w_b),
                MockContainer(w_c),
                MockContainer(w_d)
            ])
        workload_manager = WorkloadManager(cpu, docker_client)
        workload_manager.add_workloads([w_a])
        workload_manager.add_workloads([w_b])
        workload_manager.add_workloads([w_c])
        workload_manager.add_workloads([w_d])

        # A better placement after re-balance should look like this
        #
        # package 0
        #     core 0
        #         thread 0 --> a
        #         thread 1 --> a
        #     core 1
        #         thread 0 --> a
        #         thread 1 --> c        <== shared core violation
        # package 1
        #     core 0
        #         thread 0 --> b
        #         thread 1 --> b
        #     core 1
        #         thread 0 --> d
        #         thread 1 --> d

        wait_until(lambda: 0 == len(get_cross_package_violations(workload_manager.get_cpu())))
        wait_until(lambda: 1 == len(get_shared_core_violations(workload_manager.get_cpu())))
        self.assertEqual(0, workload_manager.get_queue_depth())
        self.assertEqual(0, len(workload_manager.get_cpu().get_empty_threads()))

