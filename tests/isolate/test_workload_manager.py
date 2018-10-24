import logging
import unittest
import uuid

from tests.docker.mock_docker import MockDockerClient, MockContainer
from tests.utils import wait_until
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.utils import get_cpu, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)


class TestWorkloadManager(unittest.TestCase):

    def test_single_static_workload_lifecycle(self):
        cpu = get_cpu()
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)

        docker_client = MockDockerClient([MockContainer(workload)])
        resource_manager = ResourceManager(cpu, docker_client)
        workload_manager = WorkloadManager(resource_manager)

        # Add workload
        workload_manager.add_workloads([workload])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(cpu.get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    def test_single_burst_workload_lifecycle(self):
        cpu = get_cpu()
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, BURST)

        docker_container = MockContainer(workload)
        docker_client = MockDockerClient([docker_container])
        resource_manager = ResourceManager(cpu, docker_client)
        workload_manager = WorkloadManager(resource_manager)

        # Add workload
        workload_manager.add_workloads([workload])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(docker_container.update_calls) == 1)

        # All threads should have been assigned to the only burst workload.
        update_call = docker_container.update_calls[0]
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(update_call))

        # No threads should have been consumed from the cpu model perspective.
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    def test_alternating_static_burst_workloads(self):
        cpu = get_cpu()
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
        resource_manager = ResourceManager(cpu, docker_client)
        workload_manager = WorkloadManager(resource_manager)

        # Add static workload
        workload_manager.add_workloads([static0])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(static_container0.update_calls) == 1)
        expected_free_thread_count = DEFAULT_TOTAL_THREAD_COUNT - thread_count
        self.assertEqual(expected_free_thread_count, len(cpu.get_empty_threads()))

        # Add burst workload
        workload_manager.add_workloads([burst0])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(burst_container0.update_calls) == 1)
        # No change in empty threads expected
        self.assertEqual(expected_free_thread_count, len(cpu.get_empty_threads()))

        # Add static workload
        workload_manager.add_workloads([static1])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(static_container1.update_calls) == 1)
        expected_free_thread_count = expected_free_thread_count - thread_count
        self.assertEqual(expected_free_thread_count, len(cpu.get_empty_threads()))
        # The burst0 container should be updated again because the burst footprint changed after the addition of a
        # static workload
        wait_until(lambda: len(burst_container0.update_calls) == 2)
        self.assertEqual(expected_free_thread_count, len(burst_container0.update_calls[1]))

        # Add burst workload
        workload_manager.add_workloads([burst1])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        wait_until(lambda: len(burst_container1.update_calls) == 1)
        # No change in empty threads expected
        self.assertEqual(expected_free_thread_count, len(cpu.get_empty_threads()))

    def test_remove_unknown_workload(self):
        cpu = get_cpu()
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)

        docker_client = MockDockerClient([MockContainer(workload)])
        resource_manager = ResourceManager(cpu, docker_client)
        workload_manager = WorkloadManager(resource_manager)

        # Remove from empty set
        workload_manager.remove_workloads(["unknown_workload_id"])

        # Add workload
        workload_manager.add_workloads([workload])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(cpu.get_empty_threads()))

        # Removal of an unknown workload should have no effect
        workload_manager.remove_workloads(["unknown_workload_id"])
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(cpu.get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        wait_until(lambda: workload_manager.get_queue_depth() == 0)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))
