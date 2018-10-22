import unittest
import uuid

from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.utils import config_logs

config_logs()


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

        t1.free()
        self.assertEqual([t0, t2, t1, t3], p.get_empty_threads())
