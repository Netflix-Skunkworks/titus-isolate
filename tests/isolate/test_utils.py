import unittest

from tests.config.test_property_provider import TestPropertyProvider
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import ALLOCATOR_KEY, NOOP
from titus_isolate.isolate.utils import get_allocator_class


class TestUtils(unittest.TestCase):

    def test_get_noop_cpu_allocator(self):
        property_provider = TestPropertyProvider(
            {
               ALLOCATOR_KEY: NOOP
            })
        config_manager = ConfigManager(property_provider)
        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator_class)
