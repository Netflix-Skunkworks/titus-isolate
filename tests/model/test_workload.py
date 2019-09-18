import unittest
import uuid

from tests.utils import get_test_workload
from titus_isolate.event.constants import STATIC, BURST


class TestWorkload(unittest.TestCase):

    def test_construction(self):
        identifier = uuid.uuid4()
        thread_count = 2
        workload_type = STATIC

        w = get_test_workload(identifier, thread_count, workload_type)
        self.assertEqual(identifier, w.get_id())
        self.assertEqual(thread_count, w.get_thread_count())
        self.assertEqual(workload_type, w.get_type())

    def test_invalid_workload(self):
        with self.assertRaises(ValueError):
            get_test_workload(uuid.uuid4(), 1, "UNKNOWN_WORKLOAD_TYPE")

        with self.assertRaises(ValueError):
            get_test_workload(uuid.uuid4(), -1, BURST)

        with self.assertRaises(ValueError):
            get_test_workload(BURST, 1, STATIC)
