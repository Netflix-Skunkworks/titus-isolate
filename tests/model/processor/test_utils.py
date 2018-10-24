import logging
import unittest
import uuid

from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.processor.utils import get_emptiest_core
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)


class TestUtils(unittest.TestCase):

    def test_get_emptiest_core(self):
        c0 = Core(0, [Thread(0), Thread(2)])
        c1 = Core(1, [Thread(1), Thread(3)])

        # The first core should be the emptiest
        p = Package(0, [c0, c1])
        self.assertEqual(c0, get_emptiest_core(p))

        # The second core should be emptiest after we claim a thread on the first
        c0.get_threads()[0].claim(uuid.uuid4())
        self.assertEqual(c1, get_emptiest_core(p))

        # The first core should be the emptiest again, after we release the claimed thread
        c0.get_threads()[0].free()
        self.assertEqual(c0, get_emptiest_core(p))

        # The first core should be emptiest when we claim a thread on the second
        c1.get_threads()[1].claim(uuid.uuid4())
        self.assertEqual(c0, get_emptiest_core(p))

        # When an equal number of threads are claimed on both cores, the first should be returned
        c0.get_threads()[1].claim(uuid.uuid4())
        self.assertEqual(c0, get_emptiest_core(p))
