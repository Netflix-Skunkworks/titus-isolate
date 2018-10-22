import time
import unittest
import uuid

from tests.docker.mock_docker import MockDockerClient
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.utils import get_cpu, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs()


class TestWorkloadManager(unittest.TestCase):

    def test_single_workload_lifecycle(self):
        cpu = get_cpu()
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count)

        resource_manager = ResourceManager(cpu, MockDockerClient())
        workload_manager = WorkloadManager(resource_manager)

        # Add workload
        workload_manager.add_workloads([workload])
        self.__wait_until_queue_is_empty(workload_manager, 0.5)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(cpu.get_empty_threads()))

        # Remove workload
        workload_manager.remove_workloads([workload.get_id()])
        self.__wait_until_queue_is_empty(workload_manager, 0.5)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    @staticmethod
    def __wait_until_queue_is_empty(workload_manager, timeout, event_count=1, period=0.1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if workload_manager.get_queue_depth() == 0:
                return
            time.sleep(period)

        raise TimeoutError(
            "Expected queue to empty, but queue depth is still: '{}' within timeout: '{}'.".format(
                workload_manager.get_queue_depth(), timeout))
