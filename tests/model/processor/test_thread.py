import logging
import unittest
import uuid

from titus_isolate.model.processor.thread import Thread
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)


class TestThread(unittest.TestCase):
    def test_construction(self):
        thread0 = Thread(0)
        self.assertEqual(0, thread0.get_id())

    def test_invalid_thread(self):
        with self.assertRaises(ValueError):
            Thread(-1)

        with self.assertRaises(ValueError):
            Thread("foo")

    def test_claim(self):
        workload_id = uuid.uuid4()

        t = Thread(42)
        self.assertEqual(None, t.get_workload_id())

        t.claim(workload_id)
        self.assertEqual(workload_id, t.get_workload_id())

        t.free()
        self.assertEqual(None, t.get_workload_id())
