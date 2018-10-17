import unittest
import uuid

from titus_isolate.model.core import Core
from titus_isolate.model.cpu import Cpu
from titus_isolate.model.package import Package
from titus_isolate.model.thread import Thread


class TestCpu(unittest.TestCase):
    def test_construction(self):
        p0 = Package([
            Core([Thread(0), Thread(4)]),
            Core([Thread(1), Thread(5)])])
        p1 = Package([
            Core([Thread(2), Thread(6)]),
            Core([Thread(3), Thread(7)])])

        packages = [p0, p1]
        cpu = Cpu(packages)
        self.assertEqual(packages, cpu.get_packages())

    def test_invalid_cpu(self):
        with self.assertRaises(ValueError):
            Cpu([])

    def test_get_emptiest_package(self):
        t0 = Thread(0)
        t1 = Thread(1)
        t2 = Thread(2)
        t3 = Thread(3)
        t4 = Thread(4)
        t5 = Thread(5)
        t6 = Thread(6)
        t7 = Thread(7)

        p0 = Package([
            Core([t0, t4]),
            Core([t1, t5])])
        p1 = Package([
            Core([t2, t6]),
            Core([t3, t7])])

        cpu = Cpu([p0, p1])

        # The first package should be the emptiest
        self.assertEqual(p0, cpu.get_emptiest_package())

        # The second package should be the emptiest after we claim a thread on the first
        t5.claim(uuid.uuid4())
        self.assertEqual(p1, cpu.get_emptiest_package())

        # The first package should be the emptiest again, after we release the claimed thread
        t5.clear()
        self.assertEqual(p0, cpu.get_emptiest_package())

        # The first package should be emptiest when we claim a thread on the second
        t3.claim(uuid.uuid4())
        self.assertEqual(p0, cpu.get_emptiest_package())

        # When an equal number of threads are claimed on both packages, the first should be returned
        t4.claim(uuid.uuid4())
        self.assertEqual(p0, cpu.get_emptiest_package())
