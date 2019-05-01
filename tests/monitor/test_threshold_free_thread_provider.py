import logging
import unittest

from tests.utils import config_logs, get_test_workload, DEFAULT_TEST_REQUEST_METADATA
from titus_isolate import log
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.config.constants import DEFAULT_TOTAL_THRESHOLD
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.monitor.oversubscribe_free_thread_provider import OversubscribeFreeThreadProvider
from titus_isolate.monitor.threshold_free_thread_provider import ThresholdFreeThreadProvider

config_logs(logging.DEBUG)
TEST_WORKLOAD_THREAD_COUNT = 4
TEST_THRESHOLD_USAGE = DEFAULT_TOTAL_THRESHOLD * TEST_WORKLOAD_THREAD_COUNT


class TestWorkloadManager(unittest.TestCase):

    def test_empty_usage_all_threads_claimed(self):
        # Assign a workload to a CPU
        cpu = get_cpu()
        workload = get_test_workload("a", len(cpu.get_threads()), STATIC)
        cpu = self.__assign_workload(cpu, workload)

        free_thread_provider = ThresholdFreeThreadProvider(total_threshold=DEFAULT_TOTAL_THRESHOLD)
        free_threads = free_thread_provider.get_free_threads(cpu, {}, {workload.get_id(): workload})
        self.assertEqual([], free_threads)

    def test_low_static_usage(self):
        # Threshold
        free_threads = self.__test_uniform_usage(
            TEST_THRESHOLD_USAGE,
            ThresholdFreeThreadProvider(DEFAULT_TOTAL_THRESHOLD))
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - TEST_WORKLOAD_THREAD_COUNT, len(free_threads))

        # Oversubscribe
        free_threads = self.__test_uniform_usage(
            TEST_THRESHOLD_USAGE,
            OversubscribeFreeThreadProvider(DEFAULT_TOTAL_THRESHOLD))
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(free_threads))

    def test_high_static_usage(self):
        # Threshold
        free_threads = self.__test_uniform_usage(
            TEST_THRESHOLD_USAGE + 0.001,
            ThresholdFreeThreadProvider(DEFAULT_TOTAL_THRESHOLD))
        self.assertEqual(TEST_WORKLOAD_THREAD_COUNT * 2, len(free_threads))

        # Oversubscribe
        free_threads = self.__test_uniform_usage(
            TEST_THRESHOLD_USAGE + 0.001,
            OversubscribeFreeThreadProvider(DEFAULT_TOTAL_THRESHOLD))
        self.assertEqual(TEST_WORKLOAD_THREAD_COUNT * 2, len(free_threads))

    def __test_uniform_usage(self, usage, provider):
        # Assign a workload to a CPU
        cpu = get_cpu()
        workload = get_test_workload("a", TEST_WORKLOAD_THREAD_COUNT, STATIC)

        cpu = self.__assign_workload(cpu, workload)
        log.info(cpu)
        w_usage = {"a": usage}

        return provider.get_free_threads(
            cpu,
            {workload.get_id(): workload},
            w_usage)

    @staticmethod
    def __assign_workload(cpu, workload):
        request = AllocateThreadsRequest(cpu, workload.get_id(), {workload.get_id(): workload}, {}, DEFAULT_TEST_REQUEST_METADATA)
        return IntegerProgramCpuAllocator().assign_threads(request).get_cpu()
