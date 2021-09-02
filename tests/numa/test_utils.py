import unittest

from titus_isolate.numa.utils import _set_numa_balancing


class TestUtils(unittest.TestCase):

    def test_set_numa_balancing(self):
        with self.assertRaises(ValueError):
            _set_numa_balancing(-1)

        with self.assertRaises(ValueError):
            _set_numa_balancing(2)