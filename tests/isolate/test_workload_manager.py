import logging
import unittest
import uuid

from tests.docker.mock_docker import MockDockerClient, MockContainer
from tests.utils import wait_until
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.utils import get_cpu, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)


class TestWorkloadManager(unittest.TestCase):

    def test_single_workload_lifecycle(self):
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
