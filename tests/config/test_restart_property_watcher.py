import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.test_exit_handler import TestExitHandler
from tests.utils import config_logs
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, NOOP, IP, GREEDY
from titus_isolate.config.restart_property_watcher import RestartPropertyWatcher
from titus_isolate.constants import ALLOCATOR_CONFIG_CHANGE_EXIT

config_logs(logging.DEBUG)


class TestCpuAllocatorWatcher(unittest.TestCase):

    def test_none_to_something_update(self):
        property_provider = TestPropertyProvider({})
        exit_handler = TestExitHandler()
        config_manager = ConfigManager(property_provider)
        self.assertEqual(None, config_manager.get_str(CPU_ALLOCATOR))
        watcher = RestartPropertyWatcher(config_manager, exit_handler, [CPU_ALLOCATOR])

        property_provider.map[CPU_ALLOCATOR] = GREEDY
        watcher.detect_changes()
        self.assertEqual(ALLOCATOR_CONFIG_CHANGE_EXIT, exit_handler.last_code)

    def test_nothing_to_no_change_update(self):
        property_provider = TestPropertyProvider({})
        exit_handler = TestExitHandler()
        config_manager = ConfigManager(property_provider)
        self.assertEqual(None, config_manager.get_str(CPU_ALLOCATOR))
        watcher = RestartPropertyWatcher(config_manager, exit_handler, [CPU_ALLOCATOR])

        watcher.detect_changes()
        self.assertEqual(None, exit_handler.last_code)

    def test_noop_to_ip_update(self):
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: NOOP
            })
        exit_handler = TestExitHandler()
        config_manager = ConfigManager(property_provider)
        watcher = RestartPropertyWatcher(config_manager, exit_handler, [CPU_ALLOCATOR])

        # No change yet
        watcher.detect_changes()
        self.assertEqual(None, exit_handler.last_code)

        # titus-isolate should exit when the allocator changes
        property_provider.map[CPU_ALLOCATOR] = IP
        watcher.detect_changes()
        self.assertEqual(ALLOCATOR_CONFIG_CHANGE_EXIT, exit_handler.last_code)
