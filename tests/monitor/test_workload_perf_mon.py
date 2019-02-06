import unittest
import uuid
from unittest.mock import MagicMock

from titus_isolate.docker.constants import STATIC
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.cgroup_metrics_provider import CgroupMetricsProvider
from titus_isolate.monitor.cpu_usage import CpuUsage, CpuUsageSnapshot
from titus_isolate.monitor.workload_perf_mon import WorkloadPerformanceMonitor, TIMESTAMP


class TestWorkloadPerfMon(unittest.TestCase):

    def test_single_sample(self):
        workload = Workload(uuid.uuid4(), 2, STATIC)
        metrics_provider = CgroupMetricsProvider(workload)
        perf_mon = WorkloadPerformanceMonitor(metrics_provider)

        # Initial state should just be an empty timestamps buffer
        buffers = perf_mon.get_raw_buffers()
        self.assertEqual(1, len(buffers))
        self.assertEqual(0, len(buffers[TIMESTAMP]))

        # Expect no change because no workload is really running and we haven't started mocking anything
        perf_mon.sample()
        self.assertEqual(1, len(buffers))

        # Mock reporting metrics on a single hardware thread
        cpu_usage = CpuUsage(pu_id=0, user=100, system=50)
        snapshot = CpuUsageSnapshot(timestamp=1000, rows=[cpu_usage])
        metrics_provider.get_cpu_usage = MagicMock(return_value=snapshot)
        perf_mon.sample()

        buffers = perf_mon.get_raw_buffers()
        self.assertEqual(2, len(buffers))
        self.assertEqual(1, len(buffers[TIMESTAMP]))

        buffer = buffers[str(cpu_usage.pu_id)]
        self.assertEqual(1, len(buffer))
        self.assertEqual(cpu_usage.user + cpu_usage.system, buffer[0])

