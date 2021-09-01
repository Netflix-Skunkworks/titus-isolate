import unittest
import uuid

from tests.utils import get_test_workload


class TestWorkload(unittest.TestCase):

    def test_construction(self):
        identifier = uuid.uuid4()
        thread_count = 2

        w = get_test_workload(identifier, thread_count)
        self.assertEqual(identifier, w.get_task_id())
        self.assertEqual(thread_count, w.get_thread_count())