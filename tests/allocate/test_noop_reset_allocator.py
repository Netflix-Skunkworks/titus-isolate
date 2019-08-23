import logging
import unittest
import uuid

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.utils import config_logs, get_test_workload, DEFAULT_TEST_REQUEST_METADATA, get_no_usage_threads_request
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu

config_logs(logging.DEBUG)


class TestCpu(unittest.TestCase):

    def test_assign_threads(self):
        cpu = get_cpu()
        cgroup_manager = MockCgroupManager()
        cpu_allocator = NoopResetCpuAllocator("", cgroup_manager)

        w = get_test_workload(uuid.uuid4(), 1, STATIC)
        request = get_no_usage_threads_request(cpu, [w])
        cpu_allocator.assign_threads(request)
        self.assertEqual(1, cgroup_manager.container_update_counts[w.get_id()])
        self.assertEqual(len(cpu.get_threads()), len(cgroup_manager.container_update_map[w.get_id()]))

