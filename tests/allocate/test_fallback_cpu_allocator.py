import unittest

from tests.allocate.crashing_allocators import CrashingAllocator
from tests.utils import get_test_workload, get_allocate_request
from titus_isolate.allocate.fall_back_cpu_allocator import FallbackCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator

from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.model.processor.config import get_cpu


class TestFallbackCpuAllocator(unittest.TestCase):

    def test_naive_fallback(self):

        w_a = get_test_workload("a", 3)
        w_b = get_test_workload("b", 2)
        w_c = get_test_workload("c", 1)
        w_d = get_test_workload("d", 2)

        cpu = get_cpu(package_count=2, cores_per_package=2, threads_per_core=2)

        allocator = FallbackCpuAllocator(CrashingAllocator(), NaiveCpuAllocator())

        request = get_allocate_request(cpu, [w_a])
        cpu = allocator.isolate(request).get_cpu()

        request = get_allocate_request(cpu, [w_a, w_b])
        cpu = allocator.isolate(request).get_cpu()

        request = get_allocate_request(cpu, [w_b, w_a])
        cpu = allocator.isolate(request).get_cpu()

        request = get_allocate_request(cpu, [w_b, w_c])
        cpu = allocator.isolate(request).get_cpu()

        request = get_allocate_request(cpu, [w_c, w_b])
        cpu = allocator.isolate(request).get_cpu()

        request = get_allocate_request(cpu, [w_c, w_d])
        cpu = allocator.isolate(request).get_cpu()

        self.assertEqual(3, len(cpu.get_claimed_threads()))
        self.assertEqual(6, allocator.get_fallback_allocator_calls_count())

    def test_allocators_that_are_none(self):
        with self.assertRaises(ValueError):
            FallbackCpuAllocator(GreedyCpuAllocator(), None)

        with self.assertRaises(ValueError):
            FallbackCpuAllocator(None, GreedyCpuAllocator())

        with self.assertRaises(ValueError):
            FallbackCpuAllocator(None, None)
