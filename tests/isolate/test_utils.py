import unittest

from tests.config.test_property_provider import TestPropertyProvider
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import ALLOCATOR_KEY, NOOP, AB_TEST, GREEDY, CPU_ALLOCATOR_B, CPU_ALLOCATOR_A, IP, \
    EC2_INSTANCE_ID
from titus_isolate.isolate.utils import get_allocator_class, get_ab_bucket


class TestUtils(unittest.TestCase):

    def test_get_noop_cpu_allocator(self):
        property_provider = TestPropertyProvider(
            {
               ALLOCATOR_KEY: NOOP
            })
        config_manager = ConfigManager(property_provider)
        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator_class)

    def test_ab_allocator_selection(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: even_instance_id,
            })
        config_manager = ConfigManager(property_provider)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(IntegerProgramCpuAllocator, allocator_class)

        odd_instance_id = 'i-0cfefd19c9a8db977'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: odd_instance_id
            })
        config_manager = ConfigManager(property_provider)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(GreedyCpuAllocator, allocator_class)

    def test_ab_allocator_fallback(self):
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST
            })
        config_manager = ConfigManager(property_provider)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator_class)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator_class)

    def test_real_instance_ids(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: even_instance_id
            })
        config_manager = ConfigManager(property_provider)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(IntegerProgramCpuAllocator, allocator_class)

        odd_instance_id = 'i-0cfefd19c9a8db977'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: odd_instance_id
            })
        config_manager = ConfigManager(property_provider)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(GreedyCpuAllocator, allocator_class)

    def test_undefined_instance_id(self):
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY
            })
        config_manager = ConfigManager(property_provider)

        allocator_class = get_allocator_class(config_manager)
        self.assertEqual(NoopCpuAllocator, allocator_class)

    def test_get_ab_bucket(self):
        even_instance_id = 'i-0cfefd19c9a8db976'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: even_instance_id
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("A", get_ab_bucket(config_manager))

        odd_instance_id = 'i-0cfefd19c9a8db977'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: odd_instance_id
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("B", get_ab_bucket(config_manager))

        letter_instance_id = 'i-0cfefd19c9a8db97x'
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY,
                EC2_INSTANCE_ID: letter_instance_id
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("A", get_ab_bucket(config_manager))

    def test_get_ab_bucket_undefined(self):
        property_provider = TestPropertyProvider(
            {
                ALLOCATOR_KEY: AB_TEST,
                CPU_ALLOCATOR_A: IP,
                CPU_ALLOCATOR_B: GREEDY
            })
        config_manager = ConfigManager(property_provider)
        self.assertEqual("UNDEFINED", get_ab_bucket(config_manager))
