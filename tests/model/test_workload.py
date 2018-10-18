import unittest
import uuid

from titus_isolate.model.workload import Workload


class TestWorkload(unittest.TestCase):

    def test_construction(self):
        identifier = uuid.uuid4()
        thread_count = 2

        w = Workload(identifier, thread_count)
        self.assertEqual(identifier, w.get_id())
        self.assertEqual(2, w.get_thread_count())

    def test_invalid_workload(self):
        with self.assertRaises(ValueError):
            Workload(uuid.uuid4(), -1)
