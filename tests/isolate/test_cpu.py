import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.cpu import assign_threads, free_threads
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import is_cpu_full, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload

config_logs(logging.DEBUG)


class TestCpu(unittest.TestCase):

    def test_assign_one_thread_empty_cpu(self):
        """
        Workload 0: 1 thread --> (p:0 c:0 t:0)
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
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        """
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), 2, STATIC)

        threads = assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 2, len(cpu.get_empty_threads()))

        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        core01 = cpu.get_packages()[0].get_cores()[1]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        thread1 = core01.get_threads()[0]
        self.assertEqual(1, thread1.get_id())

        # Actual assigned threads
        self.assertEqual(2, len(threads))
        self.assertEqual(thread0, threads[0])
        self.assertEqual(thread1, threads[1])

    def test_assign_two_workloads_empty_cpu(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        Workload 1: 1 thread  --> (p:1 c:0 t:0)
        """
        cpu = get_cpu()
        w0 = Workload(uuid.uuid4(), 2, STATIC)
        w1 = Workload(uuid.uuid4(), 1, STATIC)

        threads0 = assign_threads(cpu, w0)
        threads1 = assign_threads(cpu, w1, {w0.get_id(): 0})
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 3, len(cpu.get_empty_threads()))

        packages = cpu.get_packages()

        # WORKLOAD 0
        # Expected core and threads
        core00 = packages[0].get_cores()[0]
        core01 = packages[0].get_cores()[1]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        thread1 = core01.get_threads()[0]
        self.assertEqual(1, thread1.get_id())

        # Actual assigned threads
        self.assertEqual(2, len(threads0))
        self.assertEqual(thread0, threads0[0])
        self.assertEqual(thread1, threads0[1])

        # WORKLOAD 1
        # Expected core and threads
        core00 = packages[1].get_cores()[0]
        thread4 = core00.get_threads()[0]
        self.assertEqual(4, thread4.get_id())

        self.assertEqual(1, len(threads1))
        self.assertEqual(thread4, threads1[0])

    def test_assign_ten_threads_empty_cpu(self):
        """
        Workload 0: 10 threads --> (p:0 c:[0-7] t:[0-9])
        | 1 | 1 | 1 | 1 |
        | 1 | 1 |   |   |
        | ------------- |
        | 1 | 1 | 1 | 1 |
        |   |   |   |   |
        """
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), 10, STATIC)

        threads = assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 10, len(cpu.get_empty_threads()))

        expected_thread_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

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

        thread_assignments = [assign_threads(cpu, w,
            {ow.get_id(): j for j, ow in enumerate(workloads[:i])}) for i, w in enumerate(workloads)]

        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(8, len(thread_assignments[0]))
        self.assertEqual(4, len(thread_assignments[1]))
        self.assertEqual(2, len(thread_assignments[2]))
        self.assertEqual(1, len(thread_assignments[3]))
        self.assertEqual(1, len(thread_assignments[4]))

    def test_filling_holes(self):
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
        [assign_threads(cpu, w,
            {ow.get_id(): j for j, ow in enumerate(workloads[:i+1])})
         for i, w in enumerate(workloads[1:])]

        self.assertEqual(0, len(cpu.get_empty_threads()))

        # first workload should be filling completely a socket to avoid cross-socket job layout
        for package in cpu.get_packages():
            if package.get_cores()[0].get_threads()[0].get_workload_id() != wa.get_id():
                continue
            ids = [t.get_workload_id() for core in package.get_cores() for t in core.get_threads()]
            self.assertListEqual(ids, [wa.get_id()] * 8)

    def test_assign_to_full_cpu_fails(self):
        # Fill the CPU
        cpu = get_cpu()
        w0 = Workload(uuid.uuid4(), DEFAULT_TOTAL_THREAD_COUNT, STATIC)
        assign_threads(cpu, w0)
        self.assertTrue(is_cpu_full(cpu))

        # Fail to claim one more thread
        w1 = Workload(uuid.uuid4(), 1, STATIC)
        with self.assertRaises(ValueError):
            assign_threads(cpu, w1, {w0.get_id(): 0})

    def test_free_cpu(self):
        cpu = get_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w = Workload(uuid.uuid4(), 3, STATIC)
        assign_threads(cpu, w)
        self.assertEqual(
            DEFAULT_TOTAL_THREAD_COUNT - w.get_thread_count(),
            len(cpu.get_empty_threads()))

        free_threads(cpu, w.get_id(), {w.get_id(): 0})
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    def test_free_cpu_3_workloads(self):
        # Add 3 workloads sequentially, and then remove the 2nd one added.
        cpu = get_cpu()

        w0 = Workload(123, 3, STATIC)
        w1 = Workload(456, 2, STATIC)
        w2 = Workload(789, 4, STATIC)
        assign_threads(cpu, w0)
        assign_threads(cpu, w1, {w0.get_id(): 42})
        assign_threads(cpu, w2, {w0.get_id(): 42, w1.get_id(): 43})
        self.assertEqual(
            DEFAULT_TOTAL_THREAD_COUNT - 3 - 4 - 2,
            len(cpu.get_empty_threads()))

        free_threads(cpu, w1.get_id(), {w0.get_id(): 42, w1.get_id(): 43, w2.get_id(): 77})
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 3 - 4, len(cpu.get_empty_threads()))

        workload_ids_left = set()
        for t in cpu.get_threads():
            if t.is_claimed():
                workload_ids_left.add(t.get_workload_id())

        self.assertListEqual(sorted(list(workload_ids_left)), [123, 789])
