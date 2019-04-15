import logging
import unittest
from unittest.mock import MagicMock

from tests.utils import config_logs, get_test_workload, DEFAULT_TEST_INSTANCE_ID
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.config.constants import DEFAULT_PER_WORKLOAD_THRESHOLD
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.monitor.cpu_usage_provider import CpuUsageProvider
from titus_isolate.monitor.threshold_free_thread_provider import ThresholdFreeThreadProvider
from titus_isolate.monitor.workload_monitor_manager import DEFAULT_SAMPLE_FREQUENCY_SEC
from titus_isolate.utils import set_workload_monitor_manager

TEST_TOTAL_DURATION_SEC = 60
TEST_TOTAL_THRESHOLD = 0.1
TEST_PER_WORKLOAD_THRESHOLD = 0.05

config_logs(logging.DEBUG)


class TestCpuUsageProvider(CpuUsageProvider):
    def __init__(
            self,
            per_workload_usage,
            total_usage,
            per_workload_duration_sec=DEFAULT_SAMPLE_FREQUENCY_SEC,
            total_workload_duration_sec=TEST_TOTAL_DURATION_SEC):

        self.__usage = {
            per_workload_duration_sec: per_workload_usage,
            total_workload_duration_sec: total_usage
        }

    def get_cpu_usage(self, seconds: int, agg_granularity_secs : int) -> dict:
        return self.__usage[seconds]


class TestWorkloadManager(unittest.TestCase):

    def test_empty_usage_all_threads_claimed(self):
        # Assign a workload to a CPU
        cpu = get_cpu()
        workload = get_test_workload("a", len(cpu.get_threads()), STATIC)
        cpu = self.__assign_workload(cpu, workload)

        # Fake empty CPU Usage
        cpu_usage_provider = CpuUsageProvider()
        cpu_usage_provider.get_cpu_usage = MagicMock(return_value={})
        set_workload_monitor_manager(cpu_usage_provider)

        # Setup thresholds
        free_thread_provider = ThresholdFreeThreadProvider(
            total_threshold=TEST_TOTAL_THRESHOLD,
            total_duration_sec=TEST_TOTAL_DURATION_SEC,
            per_workload_threshold=TEST_PER_WORKLOAD_THRESHOLD,
            per_workload_duration_sec=DEFAULT_SAMPLE_FREQUENCY_SEC)

        free_threads = free_thread_provider.get_free_threads(cpu)

        # No threads shold be free
        self.assertEqual([], free_threads)

    def test_low_usage_all_threads_claimed(self):
        thread_count = len(get_cpu().get_threads())
        free_threads = self.__test_uniform_usage(DEFAULT_PER_WORKLOAD_THRESHOLD)
        self.assertEqual(thread_count, len(free_threads))

    def test_high_usage_all_threads_claimed(self):
        free_threads = self.__test_uniform_usage(DEFAULT_PER_WORKLOAD_THRESHOLD + 0.001)
        self.assertEqual([], free_threads)

    def __test_uniform_usage(self, usage):
        # Assign a workload to a CPU
        cpu = get_cpu()
        thread_count = len(cpu.get_threads())
        workload = get_test_workload("a", thread_count, STATIC)
        cpu = self.__assign_workload(cpu, workload)

        # Low uniform CPU usage
        w_usage = {}
        for x in range(thread_count):
            w_usage[str(x)] = usage
        low_cpu_usage = {
            workload.get_id(): w_usage
        }
        set_workload_monitor_manager(TestCpuUsageProvider(low_cpu_usage, low_cpu_usage))

        # Setup thresholds
        free_thread_provider = ThresholdFreeThreadProvider(
            total_threshold=TEST_TOTAL_THRESHOLD,
            total_duration_sec=TEST_TOTAL_DURATION_SEC,
            per_workload_threshold=TEST_PER_WORKLOAD_THRESHOLD,
            per_workload_duration_sec=DEFAULT_SAMPLE_FREQUENCY_SEC)

        return free_thread_provider.get_free_threads(cpu)

    @staticmethod
    def __assign_workload(cpu, workload):
        return IntegerProgramCpuAllocator().assign_threads(
            cpu,
            workload.get_id(),
            {workload.get_id(): workload},
            {},
            DEFAULT_TEST_INSTANCE_ID)

