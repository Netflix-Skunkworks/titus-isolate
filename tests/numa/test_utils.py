import unittest

from tests.utils import get_test_workload
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.numa.utils import _set_numa_balancing, _occupies_entire_cpu


class TestUtils(unittest.TestCase):

    def test_set_numa_balancing(self):
        with self.assertRaises(ValueError):
            _set_numa_balancing(-1)

        with self.assertRaises(ValueError):
            _set_numa_balancing(2)

    def test_occupies_entire_cpu(self):
        cpu = get_cpu()

        workload = get_test_workload("a", len(cpu.get_threads()), STATIC)
        self.assertTrue(_occupies_entire_cpu(workload, cpu))

        workload = get_test_workload("a", len(cpu.get_threads()) - 1, STATIC)
        self.assertFalse(_occupies_entire_cpu(workload, cpu))
