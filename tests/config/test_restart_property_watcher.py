import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.test_exit_handler import TestExitHandler
from tests.utils import config_logs
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, NOOP, IP, AB_TEST, CPU_ALLOCATOR_A, CPU_ALLOCATOR_B, \
    EC2_INSTANCE_ID, GREEDY
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

    def test_ab_classification_swap(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: NOOP,
                CPU_ALLOCATOR_B: IP,
                EC2_INSTANCE_ID: even_instance_id
            })
        exit_handler = TestExitHandler()
        config_manager = ConfigManager(property_provider)
        watcher = RestartPropertyWatcher(config_manager, exit_handler, [CPU_ALLOCATOR])

        # No change yet
        watcher.detect_changes()
        self.assertEqual(None, exit_handler.last_code)

        # Swap A and B to simulate instance classification change
        # N.B. the ALLOCATOR_KEY and EC_INSTANCE_ID do NOT change
        property_provider.map[CPU_ALLOCATOR_A] = IP
        property_provider.map[CPU_ALLOCATOR_B] = NOOP
        watcher.detect_changes()
        self.assertEqual(ALLOCATOR_CONFIG_CHANGE_EXIT, exit_handler.last_code)
