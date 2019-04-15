import unittest

from tests.allocate.crashing_allocators import CrashingAllocator
from tests.utils import get_test_workload, DEFAULT_TEST_INSTANCE_ID
from titus_isolate.allocate.fall_back_cpu_allocator import FallbackCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu


class TestFallbackCpuAllocator(unittest.TestCase):

    def test_ip_fallback(self):

        w_a = get_test_workload("a", 3, STATIC)
        w_b = get_test_workload("b", 2, STATIC)
        w_c = get_test_workload("c", 1, STATIC)
        w_d = get_test_workload("d", 2, STATIC)

        cpu = get_cpu(package_count=2, cores_per_package=2, threads_per_core=2)

        allocator = FallbackCpuAllocator(CrashingAllocator(), IntegerProgramCpuAllocator())
        workloads = {}

        workloads[w_a.get_id()] = w_a
        cpu = allocator.assign_threads(cpu, w_a.get_id(), workloads, {}, DEFAULT_TEST_INSTANCE_ID)

        workloads[w_b.get_id()] = w_b
        cpu = allocator.assign_threads(cpu, w_b.get_id(), workloads, {}, DEFAULT_TEST_INSTANCE_ID)

        cpu = allocator.free_threads(cpu, "a", workloads, {}, DEFAULT_TEST_INSTANCE_ID)
        workloads.pop("a")

        workloads[w_c.get_id()] = w_c
        cpu = allocator.assign_threads(cpu, w_c.get_id(), workloads, {}, DEFAULT_TEST_INSTANCE_ID)

        cpu = allocator.free_threads(cpu, "b", workloads, {}, DEFAULT_TEST_INSTANCE_ID)
        workloads.pop("b")

        workloads[w_d.get_id()] = w_d
        cpu = allocator.assign_threads(cpu, w_d.get_id(), workloads, {}, DEFAULT_TEST_INSTANCE_ID)

        self.assertEqual(3, len(cpu.get_claimed_threads()))
        self.assertEqual(6, allocator.get_fallback_allocator_calls_count())

    def test_allocators_that_are_none(self):
        with self.assertRaises(ValueError):
            FallbackCpuAllocator(GreedyCpuAllocator(), None)

        with self.assertRaises(ValueError):
            FallbackCpuAllocator(None, GreedyCpuAllocator())

        with self.assertRaises(ValueError):
            FallbackCpuAllocator(None, None)
