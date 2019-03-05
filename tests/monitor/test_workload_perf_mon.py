import calendar
from collections import deque
from datetime import datetime as dt, timedelta as td
import unittest
import uuid
from unittest.mock import MagicMock

import numpy as np

from titus_isolate.docker.constants import STATIC
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.cgroup_metrics_provider import CgroupMetricsProvider
from titus_isolate.monitor.cpu_usage import CpuUsage, CpuUsageSnapshot
from titus_isolate.monitor.workload_monitor_manager import DEFAULT_SAMPLE_FREQUENCY_SEC
from titus_isolate.monitor.workload_perf_mon import WorkloadPerformanceMonitor


class TestWorkloadPerfMon(unittest.TestCase):

    def test_single_sample(self):
        workload = Workload(uuid.uuid4(), 2, STATIC)
        metrics_provider = CgroupMetricsProvider(workload)
        perf_mon = WorkloadPerformanceMonitor(metrics_provider, DEFAULT_SAMPLE_FREQUENCY_SEC)

        # Initial state should just be an empty timestamps buffer
        _, timestamps, buffers = perf_mon.get_buffers()
        self.assertEqual(0, len(buffers))
        self.assertEqual(0, len(timestamps))

        # Expect no change because no workload is really running and we haven't started mocking anything
        perf_mon.sample()
        self.assertEqual(0, len(buffers))

        # Mock reporting metrics on a single hardware thread
        cpu_usage = CpuUsage(pu_id=0, user=100, system=50)
        snapshot = CpuUsageSnapshot(timestamp=dt.now(), rows=[cpu_usage])
        metrics_provider.get_cpu_usage = MagicMock(return_value=snapshot)
        perf_mon.sample()

        _, timestamps, buffers = perf_mon.get_buffers()
        self.assertEqual(1, len(buffers))
        self.assertEqual(1, len(timestamps))

        buffer = buffers[cpu_usage.pu_id]
        self.assertEqual(1, len(buffer))
        self.assertEqual(cpu_usage.user + cpu_usage.system, buffer[0])

    def test_monitor_cpu_usage_normalization(self):
        to_ts = lambda d: calendar.timegm(d.timetuple())

        data = WorkloadPerformanceMonitor.normalize_data(
            to_ts(dt(2019, 3, 5, 10, 15, 0)),
            list(map(to_ts, [dt(2019, 3, 5, 10, 14, 30),
             dt(2019, 3, 5, 10, 14, 11),
             dt(2019, 3, 5, 10, 13, 28)])),
            [deque([100, 200, 200], 100), deque([50, 300, 360], 100)]
            )
        self.assertEqual(360-50+200-100, data[-1])
        self.assertEqual(59, np.sum(np.isnan(data).astype(np.int16)))
