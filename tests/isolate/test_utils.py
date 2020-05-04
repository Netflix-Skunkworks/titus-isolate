import logging
import unittest
from time import sleep

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, get_test_workload
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, NOOP, NOOP_RESET
from titus_isolate.event.constants import STATIC
from titus_isolate.isolate.utils import get_fallback_allocator
from titus_isolate.model.utils import get_sorted_workloads

config_logs(logging.DEBUG)


class TestUtils(unittest.TestCase):

    def test_get_noop_cpu_allocator(self):
        property_provider = TestPropertyProvider(
            {
               CPU_ALLOCATOR: NOOP
            })
        config_manager = ConfigManager(property_provider)
        allocator = get_fallback_allocator(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_get_noop_reset_cpu_allocator(self):
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: NOOP_RESET
            })
        config_manager = ConfigManager(property_provider)
        allocator = get_fallback_allocator(config_manager)
        self.assertEqual(NoopResetCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_get_sorted_workloads(self):
        w_a = get_test_workload('a', 1, STATIC, 0)
        w_b = get_test_workload('b', 1, STATIC, 1)
        w_c = get_test_workload('c', 1, STATIC, 2)
        expected_ids = ['a', 'b', 'c']

        scrambled_workloads = [w_b, w_a, w_c]
        sorted_workloads = get_sorted_workloads(scrambled_workloads)
        actual_ids = [w.get_id() for w in sorted_workloads]

        self.assertEqual(expected_ids, actual_ids)
