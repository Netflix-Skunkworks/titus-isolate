import logging
import unittest
import uuid

from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.cpu import assign_threads, free_threads
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import is_cpu_full, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)


class TestCpu(unittest.TestCase):

    def test_assign_one_thread_empty_cpu(self):
        """
        Workload 0: 1 cores --> p:0 c:0 t:0
        """
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w = Workload(uuid.uuid4(), 1, STATIC)

        threads = assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(cpu.get_empty_threads()))
        self.assertEqual(1, len(threads))
        self.assertEqual(0, threads[0].get_id())

    def test_assign_two_threads_empty_cpu(self):
        """
        Workload 0: 2 cores --> p:0 c:0 t:[0, 8]
        """
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), 2, STATIC)

        threads = assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 2, len(cpu.get_empty_threads()))

        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        thread8 = core00.get_threads()[1]
        self.assertEqual(8, thread8.get_id())

        # Actual assigned threads
        self.assertEqual(2, len(threads))
        self.assertEqual(thread0, threads[0])
        self.assertEqual(thread8, threads[1])

    def test_assign_two_workloads_empty_cpu(self):
        """
        Workload 0: 2 cores --> p:0 c:0 t:[0, 8]
        Workload 1: 1 core  --> p:1 c:0 t:[4]
        """
        cpu = get_cpu()
        w0 = Workload(uuid.uuid4(), 2, STATIC)
        w1 = Workload(uuid.uuid4(), 1, STATIC)

        threads0 = assign_threads(cpu, w0)
        threads1 = assign_threads(cpu, w1)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 3, len(cpu.get_empty_threads()))

        # WORKLOAD 0
        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        thread8 = core00.get_threads()[1]
        self.assertEqual(8, thread8.get_id())

        # Actual assigned threads
        self.assertEqual(2, len(threads0))
        self.assertEqual(thread0, threads0[0])
        self.assertEqual(thread8, threads0[1])

        # WORKLOAD 1
        # Expected core and threads
        core00 = cpu.get_packages()[1].get_cores()[0]
        thread4 = core00.get_threads()[0]
        self.assertEqual(4, thread4.get_id())

        self.assertEqual(1, len(threads1))
        self.assertEqual(thread4, threads1[0])

    def test_assign_ten_threads_empty_cpu(self):
        """
        Workload 0: 10 cores --> p:0 c:[0-3] t:[0-3, 8-11]
                                 p:1 c:0     t:[4, 12]
        """
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), 10, STATIC)

        threads = assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 10, len(cpu.get_empty_threads()))

        expected_thread_ids = [0, 1, 2, 3, 4, 8, 9, 10, 11, 12]

        thread_ids = [thread.get_id() for thread in threads]
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
        cpu = get_cpu()
        workloads = [
            Workload(uuid.uuid4(), 8, STATIC),
            Workload(uuid.uuid4(), 4, STATIC),
            Workload(uuid.uuid4(), 2, STATIC),
            Workload(uuid.uuid4(), 1, STATIC),
            Workload(uuid.uuid4(), 1, STATIC)]

        thread_assignments = [assign_threads(cpu, w) for w in workloads]

        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(8, len(thread_assignments[0]))
        self.assertEqual(4, len(thread_assignments[1]))
        self.assertEqual(2, len(thread_assignments[2]))
        self.assertEqual(1, len(thread_assignments[3]))
        self.assertEqual(1, len(thread_assignments[4]))

    def test_filling_holes(self):
        """
        Initialize with fragmented cpu.  Workload 'a' should be placed as below, consuming 8 threads.
        0   1   2   3
        a       a
        8   9   10  11
            a       a


        4   5   6   7
            a       a
        12  13  14  15
        a       a
        """
        cpu = get_cpu()

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

        workloads = [w0, w1, w2, w3]
        list(map(lambda w: assign_threads(cpu, w), workloads))

        self.assertEqual(0, len(cpu.get_empty_threads()))

    def test_assign_to_full_cpu_fails(self):
        # Fill the CPU
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)
        assign_threads(cpu, w)
        self.assertTrue(is_cpu_full(cpu))

        # Fail to claim one more thread
        w = Workload(uuid.uuid4(), 1, STATIC)
        with self.assertRaises(ValueError):
            assign_threads(cpu, w)

    def test_free_cpu(self):
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w = Workload(uuid.uuid4(), 3, STATIC)
        assign_threads(cpu, w)
        self.assertEqual(
            DEFAULT_TOTAL_THREAD_COUNT - w.get_thread_count(),
            len(cpu.get_empty_threads()))

        free_threads(cpu, w.get_id())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))
