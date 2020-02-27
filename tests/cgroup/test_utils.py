import copy
import logging
import os
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs
from titus_isolate.cgroup.utils import _get_cgroup_path_from_list, CPUSET, get_cgroup_path_from_file, parse_cpuset
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.utils import set_config_manager

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
        self.assertEqual(expected_path, _get_cgroup_path_from_list(test_input, CPUSET))

    def test_parse_cpuset_path_failure(self):
        # Note that the cpuset line is missing when compared to the success case
        cgroups_list = copy.deepcopy(test_input)
        cgroups_list.pop(7)
        self.assertEqual(None, _get_cgroup_path_from_list(cgroups_list, CPUSET))

    def test_parse_from_file(self):
        set_config_manager(ConfigManager(TestPropertyProvider({})))
        dir = os.path.dirname(os.path.abspath(__file__))
        self.assertEqual(expected_path, get_cgroup_path_from_file(dir + "/test_cgroup_file", CPUSET))

    def test_parse_cpuset(self):
        s = "2"
        threads = parse_cpuset(s)
        self.assertEqual([2], threads)

        s = "7-9"
        threads = parse_cpuset(s)
        self.assertEqual([7, 8, 9], threads)

        s = "7-8"
        threads = parse_cpuset(s)
        self.assertEqual([7, 8], threads)

        s = "2,5,7-9,12"
        threads = parse_cpuset(s)
        self.assertEqual([2, 5, 7, 8, 9, 12], threads)

        s = "5,2,12,7-9"
        threads = sorted(parse_cpuset(s))
        self.assertEqual([2, 5, 7, 8, 9, 12], threads)


