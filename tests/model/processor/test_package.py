import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread

config_logs(logging.DEBUG)


class TestPackage(unittest.TestCase):

    def test_construction(self):
        core0 = Core(0, [Thread(0), Thread(2)])
        core1 = Core(1, [Thread(1), Thread(3)])
        cores = [core0, core1]

        package = Package(0, cores)
        self.assertEqual(2, len(package.get_cores()))
        self.assertEqual(cores, package.get_cores())

    def test_invalid_package(self):
        with self.assertRaises(ValueError):
            Package(1, [])

    def test_get_empty_threads(self):
        t0 = Thread(0)
        t1 = Thread(1)
        t2 = Thread(2)
        t3 = Thread(3)

        c0 = Core(0, [t0, t2])
        c1 = Core(1, [t1, t3])

        p = Package(1, [c0, c1])
        self.assertEqual([t0, t2, t1, t3], p.get_empty_threads())

        t1.claim(uuid.uuid4())
        self.assertEqual([t0, t2, t3], p.get_empty_threads())

        t1.clear()
        self.assertEqual([t0, t2, t1, t3], p.get_empty_threads())

    def test_equality(self):
        t_0_0 = Thread(0)
        t_0_1 = Thread(1)
        c_x = Core(0, [t_0_0, t_0_1])
        p_x = Package(0, [c_x])

        t_1_0 = Thread(0)
        t_1_1 = Thread(1)
        c_y = Core(0, [t_1_0, t_1_1])
        p_y = Package(0, [c_y])
        self.assertEqual(p_x, p_y)

        t_0_1.claim("a")
        self.assertNotEqual(p_x, p_y)

        t_1_1.claim("a")
        self.assertEqual(p_x, p_y)

        t_0_0.claim("b")
        t_1_0.claim("b")
        self.assertEqual(p_x, p_y)
