import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, NOOP
from titus_isolate.isolate.utils import get_fallback_allocator

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