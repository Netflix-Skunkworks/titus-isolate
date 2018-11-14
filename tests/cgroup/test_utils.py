import copy
import logging
import os
import time
import unittest

from tests.utils import config_logs
from titus_isolate.cgroup.utils import get_cpuset_path_from_list, get_cpuset_path_from_file, wait_for_file_to_exist, \
    MAX_FILE_WAIT_S

config_logs(logging.DEBUG)

test_input = [
    "11:perf_event:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "10:memory:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "9:cpu,cpuacct:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "8:devices:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "7:pids:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "6:blkio:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "5:hugetlb:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "4:cpuset:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "3:freezer:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "2:net_cls,net_prio:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "1:name=systemd:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868"
]

expected_path = "/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868"


class TestUtils(unittest.TestCase):

    def test_parse_cpuset_path_success(self):
        self.assertEqual(expected_path, get_cpuset_path_from_list(test_input))

    def test_parse_cpuset_path_failure(self):
        # Note that the cpuset line is missing when compared to the success case
        cgroups_list = copy.deepcopy(test_input)
        cgroups_list.pop(7)
        self.assertEqual(None, get_cpuset_path_from_list(cgroups_list))

    def test_parse_from_file(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        self.assertEqual(expected_path, get_cpuset_path_from_file(dir + "/test_cgroup_file"))

    def test_wait_for_file_to_exist(self):
        with self.assertRaises(TimeoutError) as context:
            wait_for_file_to_exist("/tmp/foo")

        wait_for_file_to_exist(__file__)