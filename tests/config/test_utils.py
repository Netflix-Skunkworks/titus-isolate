import unittest

from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.noop_allocator import NoopCpuAllocator
from titus_isolate.config.utils import get_cpu_allocator_index


class TestUtils(unittest.TestCase):

    def test_get_cpu_allocator_index(self):
        index = get_cpu_allocator_index(IntegerProgramCpuAllocator.__name__)
        self.assertEqual(1, index)

        index = get_cpu_allocator_index(GreedyCpuAllocator.__name__)
        self.assertEqual(2, index)

        index = get_cpu_allocator_index(NoopCpuAllocator.__name__)
        self.assertEqual(3, index)

        index = get_cpu_allocator_index("UnknownCpuAllocator")
        self.assertEqual(-1, index)
