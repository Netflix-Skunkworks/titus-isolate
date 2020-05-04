import logging
import unittest
import uuid

from tests.utils import get_test_workload, get_no_usage_threads_request, config_logs
from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.noop_reset_allocator import NoopResetCpuAllocator
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT

noop_reset_allocator = NoopResetCpuAllocator()

config_logs(logging.INFO)


class TestNoopResetAllocation(unittest.TestCase):

    def test_assign_one_workload_empty_cpu(self):
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w = get_test_workload(uuid.uuid4(), 1, STATIC)
        request = get_no_usage_threads_request(cpu, [w])
        cpu = noop_reset_allocator.assign_threads(request).get_cpu()
        log.info(cpu)
        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))

        for t in cpu.get_threads():
            self.assertEqual(1, len(t.get_workload_ids()))
            self.assertEqual(w.get_id(), t.get_workload_ids()[0])

    def test_assign_free_one_workload_empty_cpu(self):
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w = get_test_workload(uuid.uuid4(), 1, STATIC)
        request = get_no_usage_threads_request(cpu, [w])
        cpu = noop_reset_allocator.assign_threads(request).get_cpu()
        log.info(cpu)
        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))

        for t in cpu.get_threads():
            self.assertEqual(1, len(t.get_workload_ids()))
            self.assertEqual(w.get_id(), t.get_workload_ids()[0])

        request = get_no_usage_threads_request(cpu, [w])
        cpu = noop_reset_allocator.free_threads(request).get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    def test_assign_two_workloads(self):
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w0 = get_test_workload(uuid.uuid4(), 1, STATIC)
        w1 = get_test_workload(uuid.uuid4(), 2, STATIC)

        # Assign the first workload
        request = get_no_usage_threads_request(cpu, [w0])
        cpu = noop_reset_allocator.assign_threads(request).get_cpu()

        # Assign the second workload
        request = get_no_usage_threads_request(cpu, [w0, w1])
        cpu = noop_reset_allocator.assign_threads(request).get_cpu()

        log.info(cpu)
        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))

        for t in cpu.get_threads():
            self.assertEqual(2, len(t.get_workload_ids()))
            self.assertTrue(w0.get_id() in t.get_workload_ids())
            self.assertTrue(w1.get_id() in t.get_workload_ids())

    def test_override_previous_assignment(self):
        """
        Workload 0: 1 thread --> (p:0 c:0 t:0)
        """
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w0 = get_test_workload(uuid.uuid4(), 1, STATIC)
        w1 = get_test_workload(uuid.uuid4(), 2, STATIC)

        greedy_allocator = GreedyCpuAllocator()

        # Assign the first workload with Greedy
        request = get_no_usage_threads_request(cpu, [w0])
        cpu = greedy_allocator.assign_threads(request).get_cpu()
        log.info(cpu)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(cpu.get_empty_threads()))
        self.assertEqual(1, len(cpu.get_claimed_threads()))

        # Assign the second workload with NoopReset
        request = get_no_usage_threads_request(cpu, [w0, w1])
        cpu = noop_reset_allocator.assign_threads(request).get_cpu()
        log.info(cpu)
        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))

        for t in cpu.get_threads():
            self.assertEqual(2, len(t.get_workload_ids()))
            self.assertTrue(w0.get_id() in t.get_workload_ids())
            self.assertTrue(w1.get_id() in t.get_workload_ids())
