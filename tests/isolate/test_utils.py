import logging
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, get_test_workload
from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import CPU_ALLOCATOR, NOOP, AB_TEST, GREEDY, CPU_ALLOCATOR_B, CPU_ALLOCATOR_A, IP, \
    EC2_INSTANCE_ID
from titus_isolate.event.constants import STATIC
from titus_isolate.isolate.utils import get_allocator, get_ab_bucket, _get_ab_bucket_int
from titus_isolate.model.utils import get_sorted_workloads

config_logs(logging.DEBUG)


class TestUtils(unittest.TestCase):

    def test_get_noop_cpu_allocator(self):
        property_provider = TestPropertyProvider(
            {
               CPU_ALLOCATOR: NOOP
            })
        config_manager = ConfigManager(property_provider)
        allocator = get_allocator(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_ab_allocator_selection(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: even_instance_id,
            })
        config_manager = ConfigManager(property_provider)

        allocator = get_allocator(config_manager, 12)
        self.assertEqual(IntegerProgramCpuAllocator, allocator.get_primary_allocator().__class__)

        odd_instance_id = 'i-0cfefd19c9a8db977'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: odd_instance_id
            })
        config_manager = ConfigManager(property_provider)

        allocator = get_allocator(config_manager, 12)
        self.assertEqual(GreedyCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_ab_allocator_fallback(self):
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST
            })
        config_manager = ConfigManager(property_provider)

        allocator = get_allocator(config_manager)
        self.assertEqual(IntegerProgramCpuAllocator, allocator.get_primary_allocator().__class__)

        allocator = get_allocator(config_manager)
        self.assertEqual(IntegerProgramCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_real_instance_ids(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: even_instance_id
            })
        config_manager = ConfigManager(property_provider)

        allocator = get_allocator(config_manager, 12)
        self.assertEqual(IntegerProgramCpuAllocator, allocator.get_primary_allocator().__class__)

        odd_instance_id = 'i-0cfefd19c9a8db977'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: odd_instance_id
            })
        config_manager = ConfigManager(property_provider)

        allocator = get_allocator(config_manager, 12)
        self.assertEqual(GreedyCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_undefined_instance_id(self):
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY
            })
        config_manager = ConfigManager(property_provider)

        allocator = get_allocator(config_manager)
        self.assertEqual(IntegerProgramCpuAllocator, allocator.get_primary_allocator().__class__)

    def test_get_ab_bucket(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: even_instance_id
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("A", get_ab_bucket(config_manager, 12))

        odd_instance_id = 'i-0cfefd19c9a8db977'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: odd_instance_id
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("B", get_ab_bucket(config_manager, 12))

        letter_instance_id = 'i-0cfefd19c9a8db97x'
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: letter_instance_id
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("A", get_ab_bucket(config_manager, 12))

    def test_get_ab_bucket_undefined(self):
        property_provider = TestPropertyProvider(
            {
                CPU_ALLOCATOR: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("UNDEFINED", get_ab_bucket(config_manager, 12))

    def test_get_hourly_ab_bucket(self):
        even_hour_to_bucket_map = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            6: 1,
            7: 1,
            8: 1,
            9: 1,
            10: 1,
            11: 1,
            12: 0,
            13: 0,
            14: 0,
            15: 0,
            16: 0,
            17: 0,
            18: 1,
            19: 1,
            20: 1,
            21: 1,
            22: 1,
            23: 1
        }

        char = "4"
        for hour in range(24):
            bucket_int = _get_ab_bucket_int(char, hour)
            log.info("{}: {}".format(hour, bucket_int))
            self.assertEqual(even_hour_to_bucket_map[hour], bucket_int)

        odd_hour_to_bucket_map = {
            0: 1,
            1: 1,
            2: 1,
            3: 1,
            4: 1,
            5: 1,
            6: 0,
            7: 0,
            8: 0,
            9: 0,
            10: 0,
            11: 0,
            12: 1,
            13: 1,
            14: 1,
            15: 1,
            16: 1,
            17: 1,
            18: 0,
            19: 0,
            20: 0,
            21: 0,
            22: 0,
            23: 0
        }

        char = "3"
        for hour in range(24):
            bucket_int = _get_ab_bucket_int(char, hour)
            log.info("{}: {}".format(hour, bucket_int))
            self.assertEqual(odd_hour_to_bucket_map[hour], bucket_int)

    def test_get_sorted_workloads(self):
        w_a = get_test_workload('a', 1, STATIC)
        w_b = get_test_workload('b', 1, STATIC)
        w_c = get_test_workload('c', 1, STATIC)
        expected_ids = ['a', 'b', 'c']

        scrambled_workloads = [w_b, w_a, w_c]
        sorted_workloads = get_sorted_workloads(scrambled_workloads)
        actual_ids = [w.get_id() for w in sorted_workloads]

        self.assertEqual(expected_ids, actual_ids)
