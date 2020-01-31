import unittest

from titus_isolate.allocate.constants import CPU_USAGE
from titus_isolate.monitor.utils import parse_usage_csv, pad_usage, parse_csv_usage_heading, get_resource_usage, \
    resource_usages_to_dict

simple_csv = """Time,"cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service","cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7aad3fa0-b172-496e-87cd-032bff7daba1.service","cgroup.memory.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service","cgroup.memory.usage-/containers.slice/titus-executor@default__7aad3fa0-b172-496e-87cd-032bff7daba1.service"
2020-01-29 19:46:32,,,8343552,10649600
2020-01-29 19:47:32,1.000,1.991,8343552,10649600
2020-01-29 19:48:32,1.000,1.988,8343552,10649600
2020-01-29 19:49:32,1.000,1.991,8343552,10649600
2020-01-29 19:50:32,1.000,1.987,8343552,10649600"""


class TestCsvUsage(unittest.TestCase):

    def test_simple_parse_usage_csv(self):
        expected_headings = ["Time", "cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service", "cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7aad3fa0-b172-496e-87cd-032bff7daba1.service", "cgroup.memory.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service", "cgroup.memory.usage-/containers.slice/titus-executor@default__7aad3fa0-b172-496e-87cd-032bff7daba1.service"]

        parsed = parse_usage_csv(simple_csv)
        self.assertEqual(5, len(parsed))

        for expected_heading in expected_headings:
            self.assertTrue(expected_heading in parsed)

        padded_length = 10
        padded = pad_usage(parsed, padded_length)
        self.assertEqual(len(parsed), len(padded))

        for v in padded.values():
            self.assertEqual(padded_length, len(v))

    def test_parse_heading(self):
        raw_heading = "cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service"
        workload_id, resource_name = parse_csv_usage_heading(raw_heading)
        self.assertEqual('7b1c435b-9473-40be-b944-2b0b26e2a703', workload_id)
        self.assertEqual(CPU_USAGE, resource_name)

    def test_csv_to_resource_usage(self):
        value_count = 10
        interval_sec = 60
        usages = get_resource_usage(simple_csv, value_count, interval_sec)

        for u in usages:
            self.assertEqual(1580355632.0, u.start_time_epoch_sec)
            self.assertEqual(value_count, len(u.values))
            self.assertEqual(interval_sec, u.interval_sec)

    def test_resource_usages_to_dict(self):
        value_count = 10
        interval_sec = 60
        usages = get_resource_usage(simple_csv, value_count, interval_sec)
        d = resource_usages_to_dict(usages)
        pass
