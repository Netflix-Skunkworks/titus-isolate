import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.test_exit_handler import TestExitHandler
from tests.utils import config_logs
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import ALLOCATOR_KEY, NOOP, IP, AB_TEST, CPU_ALLOCATOR_A, CPU_ALLOCATOR_B, \
    EC2_INSTANCE_ID
from titus_isolate.config.cpu_allocator_watcher import CpuAllocatorWatcher
from titus_isolate.constants import ALLOCATOR_CONFIG_CHANGE_EXIT

CONFIG_CHANGE_INTERVAL = 0.1

config_logs(logging.DEBUG)


class TestCpuAllocatorWatcher(unittest.TestCase):

    def test_noop_to_ip_update(self):
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: NOOP
            })
        exit_handler = TestExitHandler()
        config_manager = ConfigManager(property_provider, CONFIG_CHANGE_INTERVAL, exit_handler)
        watcher = CpuAllocatorWatcher(config_manager, exit_handler, CONFIG_CHANGE_INTERVAL)

        # No change yet
        watcher.detect_allocator_change()
        self.assertEqual(None, exit_handler.last_code)

        # titus-isolate should exit when the allocator changes
        property_provider.map[ALLOCATOR_KEY] = IP
        watcher.detect_allocator_change()
        self.assertEqual(ALLOCATOR_CONFIG_CHANGE_EXIT, exit_handler.last_code)

    def test_ab_classification_swap(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: NOOP,
                CPU_ALLOCATOR_B: IP,
                EC2_INSTANCE_ID: even_instance_id
            })
        exit_handler = TestExitHandler()
        config_manager = ConfigManager(property_provider, CONFIG_CHANGE_INTERVAL, exit_handler)
        watcher = CpuAllocatorWatcher(config_manager, exit_handler, CONFIG_CHANGE_INTERVAL)

        # No change yet
        watcher.detect_allocator_change()
        self.assertEqual(None, exit_handler.last_code)

        # Swap A and B to simulate instance classification change
        # N.B. the ALLOCATOR_KEY and EC_INSTANCE_ID do NOT change
        property_provider.map[CPU_ALLOCATOR_A] = IP
        property_provider.map[CPU_ALLOCATOR_B] = NOOP
        watcher.detect_allocator_change()
        self.assertEqual(ALLOCATOR_CONFIG_CHANGE_EXIT, exit_handler.last_code)
