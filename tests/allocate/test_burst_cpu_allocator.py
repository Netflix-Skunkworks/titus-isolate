import logging
import unittest

from tests.utils import config_logs, get_threads_with_workload
from titus_isolate.allocate.burst_cpu_allocator import _is_thread_available, BurstCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload

config_logs(logging.DEBUG)


class TestBurstCpuAllocator(unittest.TestCase):

    def test_is_thread_available_for_unclaimed(self):
        t = Thread(42)
        self.assertTrue(_is_thread_available(t, None))

    def test_is_thread_available_for_static_claimed(self):
        workload = Workload("a", 2, STATIC)
        self.thread = Thread(42)
        t = self.thread
        t.claim(workload.get_id())

        self.assertFalse(_is_thread_available(t, {workload.get_id(): workload}))
    
    def test_assign_single_burst_workload(self):
        workload = Workload("a", 2, BURST)
        allocator = BurstCpuAllocator()

        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))
        
        cpu = allocator.assign_threads(get_cpu(), workload.get_id(), {workload.get_id(): workload})
        self.assertEqual(0, len(cpu.get_empty_threads()))
        for t in cpu.get_threads():
            self.assertEqual([workload.get_id()], t.get_workload_ids())

    def test_assign_multiple_burst_workload(self):
        workload_a = Workload("a", 2, BURST)
        workload_b = Workload("b", 2, BURST)
        allocator = BurstCpuAllocator()

        workloads = {
            workload_a.get_id(): workload_a
        }
        cpu = allocator.assign_threads(get_cpu(), workload_a.get_id(), workloads)

        workloads = {
            workload_a.get_id(): workload_a,
            workload_b.get_id(): workload_b
        }
        cpu = allocator.assign_threads(cpu, workload_b.get_id(), workloads)

        self.assertEqual(0, len(cpu.get_empty_threads()))
        for t in cpu.get_threads():
            self.assertEqual([workload_a.get_id(), workload_b.get_id()], t.get_workload_ids())

    def test_assign_static_burst(self):
        cpu = get_cpu()
        workload_static = Workload("a", 2, STATIC)
        workload_burst = Workload("b", 2, BURST)

        static_allocator = IntegerProgramCpuAllocator()
        burst_allocator = BurstCpuAllocator()

        # Assign a static workload
        workloads = {
            workload_static.get_id(): workload_static
        }
        cpu = static_allocator.assign_threads(cpu, workload_static.get_id(), workloads)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - workload_static.get_thread_count(), len(cpu.get_empty_threads()))

        # Assign a burst workload
        workloads = {
            workload_static.get_id(): workload_static,
            workload_burst.get_id(): workload_burst
        }
        cpu = burst_allocator.assign_threads(cpu, workload_burst.get_id(), workloads)
        self.assertEqual(0, len(cpu.get_empty_threads()))

        # Assert expected number of threads are assigned to the static workload
        self.assertEqual(
            workload_static.get_thread_count(),
            len(get_threads_with_workload(cpu, workload_static.get_id())))

        # Assert that the remaining threads are assigned to the burst workload
        self.assertEqual(
            DEFAULT_TOTAL_THREAD_COUNT - workload_static.get_thread_count(),
            len(get_threads_with_workload(cpu, workload_burst.get_id())))

        # Free the static workload, which increases the burst footprint
        cpu = burst_allocator.free_threads(cpu, workload_static.get_id(), workloads)

        # Every thread should now be assigned to the burst workload
        for t in cpu.get_threads():
            self.assertEqual([workload_burst.get_id()], t.get_workload_ids())


