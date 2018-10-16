import unittest

from titus_isolate.model.core import Core
from titus_isolate.model.package import Package
from titus_isolate.model.thread import Thread


class TestCpuModel(unittest.TestCase):

    def test_simple_construction(self):
        thread0 = Thread(0)
        self.assertEqual(0, thread0.get_processor_id())

        thread1 = Thread(1)
        self.assertEqual(1, thread1.get_processor_id())

        core = Core([thread0, thread1])
        self.assertEqual(2, len(core.get_threads()))
        self.assertEqual(thread0, core.get_threads()[0])
        self.assertEqual(thread1, core.get_threads()[1])

        package = Package([core])
        self.assertEqual(1, len(package.get_cores()))
        self.assertEqual(core, package.get_cores()[0])
