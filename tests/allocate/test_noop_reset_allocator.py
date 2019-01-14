import logging
import unittest
import uuid

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.utils import config_logs
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.docker.constants import STATIC
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload

config_logs(logging.DEBUG)


class TestCpu(unittest.TestCase):

    def test_assign_threads(self):
        cpu = get_cpu()
        cgroup_manager = MockCgroupManager()
        cpu_allocator = NoopResetCpuAllocator(cpu)
        cpu_allocator.set_cgroup_manager(cgroup_manager)

        w = Workload(uuid.uuid4(), 1, STATIC)
        cpu_allocator.assign_threads(w)
        self.assertEqual(1, cgroup_manager.container_update_counts[w.get_id()])
        self.assertEqual(len(cpu.get_threads()), len(cgroup_manager.container_update_map[w.get_id()]))

