import logging
import unittest

import titus_isolate

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class Test(unittest.TestCase):
    def setUp(self):
        self.name = "World"

    def test(self):
        titus_isolate.hello(self.name)
        assert 1 == 1
