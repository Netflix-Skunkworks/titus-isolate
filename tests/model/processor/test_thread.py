import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.model.processor.thread import Thread

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
        self.assertEqual(0, len(t.get_workload_ids()))

        t.claim(workload_id)
        self.assertEqual(1, len(t.get_workload_ids()))
        self.assertEqual(workload_id, t.get_workload_ids()[0])

        t.clear()
        self.assertEqual(0, len(t.get_workload_ids()))

    def test_multiple_claims(self):
        workload_id_a = "a"
        workload_id_b = "b"
        t = Thread(42)

        t.claim(workload_id_a)
        self.assertEqual(1, len(t.get_workload_ids()))
        self.assertEqual(workload_id_a, t.get_workload_ids()[0])
        self.assertTrue(t.is_claimed())

        t.claim(workload_id_b)
        self.assertEqual(2, len(t.get_workload_ids()))
        self.assertTrue(workload_id_a in t.get_workload_ids())
        self.assertTrue(workload_id_b in t.get_workload_ids())
        self.assertTrue(t.is_claimed())

        t.free(workload_id_a)
        self.assertEqual(1, len(t.get_workload_ids()))
        self.assertEqual(workload_id_b, t.get_workload_ids()[0])
        self.assertTrue(t.is_claimed())

        t.free(workload_id_b)
        self.assertFalse(t.is_claimed())
        self.assertEqual(0, len(t.get_workload_ids()))

    def test_free_unknown(self):
        t = Thread(42)
        self.assertEqual(0, len(t.get_workload_ids()))
        self.assertFalse(t.is_claimed())

        t.free("unknown_id")
        self.assertEqual(0, len(t.get_workload_ids()))
        self.assertFalse(t.is_claimed())

        workload_id = "a"
        t.claim(workload_id)
        t.free("unknown_id")
        self.assertEqual(1, len(t.get_workload_ids()))
        self.assertEqual(workload_id, t.get_workload_ids()[0])
        self.assertTrue(t.is_claimed())

    def test_clear_multiple_claims(self):
        workload_id_a = "a"
        workload_id_b = "b"
        t = Thread(42)

        t.claim(workload_id_a)
        t.claim(workload_id_b)
        self.assertTrue(t.is_claimed())
        self.assertEqual(2, len(t.get_workload_ids()))

        t.clear()
        self.assertFalse(t.is_claimed())
        self.assertEqual(0, len(t.get_workload_ids()))

    def test_equality(self):
        t_x = Thread(42)
        t_y = Thread(42)
        self.assertEqual(t_x, t_y)

        t_x.claim("a")
        self.assertNotEqual(t_x, t_y)

        t_y.claim("a")
        self.assertEqual(t_x, t_y)

        t_x.claim("b")
        t_y.claim("b")
        self.assertEqual(t_x, t_y)

