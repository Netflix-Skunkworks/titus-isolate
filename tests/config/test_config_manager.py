import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, wait_until
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import ALLOCATOR_KEY, GREEDY, IP
from titus_isolate.utils import start_periodic_scheduling

config_logs(logging.DEBUG)

CONFIG_CHANGE_INTERVAL = 0.1


class TestConfigManager(unittest.TestCase):

    def test_construction_without_properties(self):
        property_provider = TestPropertyProvider({})
        config_manager = ConfigManager(property_provider)
        self.assertEqual(None, config_manager.get("foo"))
        self.assertEqual(None, config_manager.get(ALLOCATOR_KEY))

    def test_none_to_something_update(self):
        property_provider = TestPropertyProvider({})
        config_manager = ConfigManager(property_provider, CONFIG_CHANGE_INTERVAL)
        self.assertEqual(None, config_manager.get(ALLOCATOR_KEY))

        start_periodic_scheduling()
        property_provider.map[ALLOCATOR_KEY] = GREEDY
        wait_until(lambda: config_manager.get(ALLOCATOR_KEY) == GREEDY)

    def test_something_to_something_update(self):
        property_provider = TestPropertyProvider(
            {
               ALLOCATOR_KEY: IP
            })
        config_manager = ConfigManager(property_provider, CONFIG_CHANGE_INTERVAL)
        self.assertEqual(IP, config_manager.get(ALLOCATOR_KEY))

        start_periodic_scheduling()
        property_provider.map[ALLOCATOR_KEY] = GREEDY
        wait_until(lambda: config_manager.get(ALLOCATOR_KEY) == GREEDY)

    def test_something_to_no_change_update(self):
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: IP
            })
        config_manager = ConfigManager(property_provider, CONFIG_CHANGE_INTERVAL)
        self.assertEqual(IP, config_manager.get(ALLOCATOR_KEY))

        original_update_count = config_manager.update_count
        start_periodic_scheduling()
        wait_until(lambda: config_manager.update_count > original_update_count)
