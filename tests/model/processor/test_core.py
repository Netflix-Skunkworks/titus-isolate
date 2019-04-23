import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.thread import Thread

config_logs(logging.DEBUG)


class TestCore(unittest.TestCase):
    def test_construction(self):
        thread0 = Thread(0)
        thread1 = Thread(1)

        core = Core(42, [thread0, thread1])
        self.assertEqual(42, core.get_id())
        self.assertEqual(2, len(core.get_threads()))
        self.assertEqual(thread0, core.get_threads()[0])
        self.assertEqual(thread1, core.get_threads()[1])

    def test_invalid_core(self):
        with self.assertRaises(ValueError):
            Core(0, [])

    def test_get_empty_threads(self):
        c = Core(1, [Thread(0), Thread(1)])
        self.assertEqual(c.get_threads(), c.get_empty_threads())

        t0 = c.get_threads()[0]
        t1 = c.get_threads()[1]

        c.get_threads()[0].claim(uuid.uuid4())
        self.assertEqual([t1], c.get_empty_threads())

        t0.clear()
        self.assertEqual(c.get_threads(), c.get_empty_threads())

        t1.claim(uuid.uuid4())
        self.assertEqual([t0], c.get_empty_threads())

        t0.claim(uuid.uuid4())
        self.assertEqual([], c.get_empty_threads())

    def test_equality(self):
        t_0_0 = Thread(0)
        t_0_1 = Thread(1)
        c_x = Core(0, [t_0_0, t_0_1])

        t_1_0 = Thread(0)
        t_1_1 = Thread(1)
        c_y = Core(0, [t_1_0, t_1_1])
        self.assertEqual(c_x, c_y)

        t_0_1.claim("a")
        self.assertNotEqual(c_x, c_y)

        t_1_1.claim("a")
        self.assertEqual(c_x, c_y)

        t_0_0.claim("b")
        t_1_0.claim("b")
        self.assertEqual(c_x, c_y)
