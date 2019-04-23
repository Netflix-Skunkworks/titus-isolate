import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread

config_logs(logging.DEBUG)


class TestCpu(unittest.TestCase):

    def test_construction(self):
        p0 = Package(0, [
            Core(0, [Thread(0), Thread(4)]),
            Core(1, [Thread(1), Thread(5)])])
        p1 = Package(1, [
            Core(0, [Thread(2), Thread(6)]),
            Core(1, [Thread(3), Thread(7)])])

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

        p0 = Package(0, [
            Core(0, [t0, t4]),
            Core(1, [t1, t5])])
        p1 = Package(1, [
            Core(0, [t2, t6]),
            Core(1, [t3, t7])])

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

    def test_equality(self):
        t_0_0 = Thread(0)
        t_0_1 = Thread(1)
        c_x = Core(0, [t_0_0, t_0_1])
        p_x = Package(0, [c_x])
        cpu_x = Cpu([p_x])

        t_1_0 = Thread(0)
        t_1_1 = Thread(1)
        c_y = Core(0, [t_1_0, t_1_1])
        p_y = Package(0, [c_y])
        cpu_y = Cpu([p_y])
        self.assertEqual(cpu_x, cpu_y)

        t_0_1.claim("a")
        self.assertNotEqual(cpu_x, cpu_y)

        t_1_1.claim("a")
        self.assertEqual(cpu_x, cpu_y)

        t_0_0.claim("b")
        t_1_0.claim("b")
        self.assertEqual(cpu_x, cpu_y)
