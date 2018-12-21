import logging
import unittest

from tests.metrics.constants import TEST_TITUS_ENVIRON_PATH, EXPECTED_TASK_ID, EXPECTED_JOB_ID, \
    TEST_NOT_TITUS_ENVIRON_PATH
from tests.utils import config_logs
from titus_isolate.metrics.linux_context_provider import TASK_ID_KEY, JOB_ID_KEY
from titus_isolate.metrics.utils import get_env_from_file

config_logs(logging.DEBUG)


class Test(unittest.TestCase):

    def test_get_env_from_titus_task_file(self):
        env_map = get_env_from_file(TEST_TITUS_ENVIRON_PATH)
        self.assertEqual(EXPECTED_TASK_ID, env_map[TASK_ID_KEY])
        self.assertEqual(EXPECTED_JOB_ID, env_map[JOB_ID_KEY])

    def test_get_env_from_random_file(self):
        env_map = get_env_from_file(TEST_NOT_TITUS_ENVIRON_PATH)
        self.assertFalse(TASK_ID_KEY in env_map.keys())
        self.assertFalse(JOB_ID_KEY in env_map.keys())
