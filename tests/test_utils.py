import unittest
from threading import Lock

import schedule

from tests.test_exit_handler import TestExitHandler
from titus_isolate.constants import SCHEDULE_ONCE_FAILURE_EXIT_CODE
from titus_isolate.utils import _schedule_once, SCHEDULING_SLEEP_INTERVAL

b = False
exit_handler = TestExitHandler()
lock = Lock()


class TestUtils(unittest.TestCase):

    def test_scheduling_exception(self):
        global b
        b = False

        exit_handler.last_code = None
        schedule.clear()

        def throw_exception():
            global b
            with lock:
                b = True
                raise Exception("test_exception")

        schedule.every(1).seconds.do(throw_exception)
        while not b:
            _schedule_once(exit_handler)

        self.assertEqual(SCHEDULE_ONCE_FAILURE_EXIT_CODE, exit_handler.last_code)

    def test_normal_scheduling(self):
        global b
        b = False

        exit_handler.last_code = None
        schedule.clear()

        def simple_execution():
            global b
            with lock:
                b = True

        schedule.every(1).seconds.do(simple_execution)
        while not b:
            _schedule_once(exit_handler)

        self.assertEqual(None, exit_handler.last_code)
