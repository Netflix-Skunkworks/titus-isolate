import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, GREEDY, IP

config_logs(logging.DEBUG)


class TestConfigManager(unittest.TestCase):

    def test_construction_without_properties(self):
        property_provider = TestPropertyProvider({})
        config_manager = ConfigManager(property_provider)
        self.assertEqual(None, config_manager.get_str("foo"))
        self.assertEqual(None, config_manager.get_str(CPU_ALLOCATOR))

    def test_none_to_something_update(self):
        property_provider = TestPropertyProvider({})
        config_manager = ConfigManager(property_provider)

        self.assertEqual(None, config_manager.get_str(CPU_ALLOCATOR))
        property_provider.map[CPU_ALLOCATOR] = GREEDY
        self.assertEqual(GREEDY, config_manager.get_str(CPU_ALLOCATOR))

    def test_something_to_something_update(self):
        property_provider = TestPropertyProvider(
            {
               CPU_ALLOCATOR: IP
            })
        config_manager = ConfigManager(property_provider)

        self.assertEqual(IP, config_manager.get_str(CPU_ALLOCATOR))
        property_provider.map[CPU_ALLOCATOR] = GREEDY
        self.assertEqual(GREEDY, config_manager.get_str(CPU_ALLOCATOR))

    def test_something_to_no_change_update(self):
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: IP
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual(IP, config_manager.get_str(CPU_ALLOCATOR))
        self.assertEqual(IP, config_manager.get_str(CPU_ALLOCATOR))
