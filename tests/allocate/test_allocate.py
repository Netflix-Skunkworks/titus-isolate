import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.docker.constants import STATIC
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import is_cpu_full, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload

config_logs(logging.DEBUG)


class TestCpu(unittest.TestCase):

    def test_assign_one_thread_empty_cpu(self):
        """
        Workload 0: 1 thread --> (p:0 c:0 t:0)
        """
        for allocator_class in [IntegerProgramCpuAllocator, GreedyCpuAllocator]:
            cpu = get_cpu()
            allocator = allocator_class(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

            w = Workload(uuid.uuid4(), 1, STATIC)

            allocator.assign_threads(w)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(cpu.get_empty_threads()))
            self.assertEqual(1, len(cpu.get_claimed_threads()))
            self.assertEqual(0, cpu.get_claimed_threads()[0].get_id())

    def test_assign_two_threads_empty_cpu_ip(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        """
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)
        w = Workload(uuid.uuid4(), 2, STATIC)

        allocator.assign_threads(w)
        self.assertEqual(2, len(cpu.get_claimed_threads()))

        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        core01 = cpu.get_packages()[0].get_cores()[1]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        self.assertTrue(thread0.is_claimed())
        thread1 = core01.get_threads()[0]
        self.assertEqual(1, thread1.get_id())
        self.assertTrue(thread1.is_claimed())

    def test_assign_two_threads_empty_cpu_greedy(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:1)
        """
        cpu = get_cpu()
        allocator = GreedyCpuAllocator(cpu)
        w = Workload(uuid.uuid4(), 2, STATIC)

        allocator.assign_threads(w)
        self.assertEqual(2, len(cpu.get_claimed_threads()))

        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        self.assertTrue(thread0.is_claimed())
        thread1 = core00.get_threads()[1]
        self.assertEqual(8, thread1.get_id())
        self.assertTrue(thread1.is_claimed())

    def test_assign_two_workloads_empty_cpu_ip(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        Workload 1: 1 thread  --> (p:1 c:0 t:0)
        """
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)
        w0 = Workload(uuid.uuid4(), 2, STATIC)
        w1 = Workload(uuid.uuid4(), 1, STATIC)

        allocator.assign_threads(w0)
        allocator.assign_threads(w1)
        self.assertEqual(3, len(cpu.get_claimed_threads()))

        packages = cpu.get_packages()

        # WORKLOAD 0
        core00 = packages[0].get_cores()[0]
        core01 = packages[0].get_cores()[1]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        self.assertTrue(thread0.is_claimed())
        thread1 = core01.get_threads()[0]
        self.assertEqual(1, thread1.get_id())
        self.assertTrue(thread1.is_claimed())

        # WORKLOAD 1
        core00 = packages[1].get_cores()[0]
        thread4 = core00.get_threads()[0]
        self.assertEqual(4, thread4.get_id())
        self.assertTrue(thread4.is_claimed())

    def test_assign_two_workloads_empty_cpu_greedy(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:0 t:1)
        Workload 1: 1 thread  --> (p:1 c:0 t:0)
        """
        cpu = get_cpu()
        allocator = GreedyCpuAllocator(cpu)
        w0 = Workload(uuid.uuid4(), 2, STATIC)
        w1 = Workload(uuid.uuid4(), 1, STATIC)

        allocator.assign_threads(w0)
        allocator.assign_threads(w1)
        self.assertEqual(3, len(cpu.get_claimed_threads()))

        packages = cpu.get_packages()

        # WORKLOAD 0
        core00 = packages[0].get_cores()[0]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        self.assertTrue(thread0.is_claimed())
        thread1 = core00.get_threads()[1]
        self.assertEqual(8, thread1.get_id())
        self.assertTrue(thread1.is_claimed())

        # WORKLOAD 1
        core00 = packages[1].get_cores()[0]
        thread4 = core00.get_threads()[0]
        self.assertEqual(4, thread4.get_id())
        self.assertTrue(thread4.is_claimed())

    def test_assign_ten_threads_empty_cpu_ip(self):
        """
        Workload 0: 10 threads --> (p:0 c:[0-7] t:[0-9])
        | 1 | 1 | 1 | 1 |
        | 1 | 1 |   |   |
        | ------------- |
        | 1 | 1 | 1 | 1 |
        |   |   |   |   |
        """
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)
        w = Workload(uuid.uuid4(), 10, STATIC)

        allocator.assign_threads(w)
        self.assertEqual(10, len(cpu.get_claimed_threads()))

        expected_thread_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        thread_ids = [thread.get_id() for thread in cpu.get_claimed_threads()]
        thread_ids.sort()

        self.assertEqual(expected_thread_ids, thread_ids)

    def test_fill_cpu(self):
        """
        Workload 0: 8 cores
        Workload 1: 4 cores
        Workload 2: 2 cores
        Workload 3: 1 core
        Workload 4: 1 core
        --------------------
        Total:      16 cores
        """
        for allocator_class in [IntegerProgramCpuAllocator, GreedyCpuAllocator]:
            cpu = get_cpu()
            allocator = allocator_class(cpu)
            workloads = [
                Workload(uuid.uuid4(), 8, STATIC),
                Workload(uuid.uuid4(), 4, STATIC),
                Workload(uuid.uuid4(), 2, STATIC),
                Workload(uuid.uuid4(), 1, STATIC),
                Workload(uuid.uuid4(), 1, STATIC)]

            tot_req = 0
            for w in workloads:
                allocator.assign_threads(w)
                tot_req += w.get_thread_count()
                self.assertEqual(tot_req, len(cpu.get_claimed_threads()))

    def test_filling_holes_ip(self):
        """
        Initialize with fragmented placement, then fill the instance. Result should be
        less fragmented, with the first workload completely filling a socket.
        | a |   | a |   |
        |   | a |   | a |
        | ------------- |
        |   | a |   | a |
        | a |   | a |   |
        """
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)

        # Initialize fragmented workload
        wa = Workload(uuid.uuid4(), 8, STATIC)

        p0 = cpu.get_packages()[0]
        p0.get_cores()[0].get_threads()[0].claim(wa.get_id())
        p0.get_cores()[1].get_threads()[1].claim(wa.get_id())
        p0.get_cores()[2].get_threads()[0].claim(wa.get_id())
        p0.get_cores()[3].get_threads()[1].claim(wa.get_id())

        p1 = cpu.get_packages()[1]
        p1.get_cores()[0].get_threads()[1].claim(wa.get_id())
        p1.get_cores()[1].get_threads()[0].claim(wa.get_id())
        p1.get_cores()[2].get_threads()[1].claim(wa.get_id())
        p1.get_cores()[3].get_threads()[0].claim(wa.get_id())

        self.assertEqual(8, len(cpu.get_empty_threads()))

        # Fill the rest of the CPU
        w0 = Workload(uuid.uuid4(), 2, STATIC)
        w1 = Workload(uuid.uuid4(), 3, STATIC)
        w2 = Workload(uuid.uuid4(), 1, STATIC)
        w3 = Workload(uuid.uuid4(), 2, STATIC)

        workloads = [wa, w0, w1, w2, w3]
        for w in workloads:
            allocator.assign_threads(w)

        self.assertEqual(0, len(cpu.get_empty_threads()))

        # first workload should be filling completely a socket to avoid cross-socket job layout
        for package in cpu.get_packages():
            if package.get_cores()[0].get_threads()[0].get_workload_id() != wa.get_id():
                continue
            ids = [t.get_workload_id() for core in package.get_cores() for t in core.get_threads()]
            self.assertListEqual(ids, [wa.get_id()] * 8)

    def test_assign_to_full_cpu_fails(self):
        for allocator_class in [IntegerProgramCpuAllocator, GreedyCpuAllocator]:
            # Fill the CPU
            cpu = get_cpu()
            allocator = allocator_class(cpu)
            w0 = Workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)
            allocator.assign_threads(w0)
            self.assertTrue(is_cpu_full(cpu))

            # Fail to claim one more thread
            w1 = Workload(uuid.uuid4(), 1, STATIC)
            with self.assertRaises(ValueError):
                allocator.assign_threads(w1)

    def test_free_cpu(self):
        for allocator_class in [IntegerProgramCpuAllocator, GreedyCpuAllocator]:
            cpu = get_cpu()
            allocator = allocator_class(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

            w = Workload(uuid.uuid4(), 3, STATIC)
            allocator.assign_threads(w)
            self.assertEqual(
                DEFAULT_TOTAL_THREAD_COUNT - w.get_thread_count(),
                len(cpu.get_empty_threads()))

            allocator.free_threads(w.get_id())
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    def test_free_cpu_3_workloads(self):
        # Add 3 workloads sequentially, and then remove the 2nd one added.
        for allocator_class in [IntegerProgramCpuAllocator, GreedyCpuAllocator]:
            cpu = get_cpu()
            allocator = allocator_class(cpu)

            w0 = Workload(123, 3, STATIC)
            w1 = Workload(456, 2, STATIC)
            w2 = Workload(789, 4, STATIC)
            allocator.assign_threads(w0)
            allocator.assign_threads(w1)
            allocator.assign_threads(w2)
            self.assertEqual(3 + 4 + 2, len(cpu.get_claimed_threads()))

            allocator.free_threads(w1.get_id())
            self.assertEqual(3 + 4, len(cpu.get_claimed_threads()))

            workload_ids_left = set()
            for t in cpu.get_threads():
                if t.is_claimed():
                    workload_ids_left.add(t.get_workload_id())

            self.assertListEqual(sorted(list(workload_ids_left)), [123, 789])

    def test_cache_ip(self):
        """
        [add a=2, add b=2, remove b=2, add c=2, remove a=2, add d=2] should lead to the following cache entries:
        (state=[], req=[2])
        (state=[2], req=[2,2])
        (state=[2,2], req=[2,0])
        [cache hit]
        [cache hit]
        (state=[2,2], req=[2,2]) but different layout
        """
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)

        allocator.assign_threads(Workload("a", 2, STATIC))
        self.assertEqual(1, len(allocator._IntegerProgramCpuAllocator__cache))

        allocator.assign_threads(Workload("b", 2, STATIC))
        self.assertEqual(2, len(allocator._IntegerProgramCpuAllocator__cache))

        allocator.free_threads("b")
        self.assertEqual(3, len(allocator._IntegerProgramCpuAllocator__cache))

        allocator.assign_threads(Workload("c", 2, STATIC))
        self.assertEqual(3, len(allocator._IntegerProgramCpuAllocator__cache))

        allocator.free_threads("a")
        self.assertEqual(4, len(allocator._IntegerProgramCpuAllocator__cache))

        allocator.assign_threads(Workload("d", 2, STATIC))
        self.assertEqual(5, len(allocator._IntegerProgramCpuAllocator__cache))