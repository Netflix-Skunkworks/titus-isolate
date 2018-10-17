import logging
import unittest
import uuid

from titus_isolate.isolate.cpu import assign_threads, get_threads
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload

DEFAULT_PACKAGE_COUNT = 2
DEFAULT_CORE_COUNT = 4
DEFAULT_THREAD_COUNT = 2
DEFAULT_TOTAL_THREAD_COUNT = DEFAULT_PACKAGE_COUNT * DEFAULT_CORE_COUNT * DEFAULT_THREAD_COUNT

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')


def __get_threads(package_index, core_index, package_count, core_count, thread_count=DEFAULT_THREAD_COUNT):
    threads = []
    for row_index in range(thread_count):
        offset = row_index * package_count * core_count
        index = offset + package_index * core_count + core_index
        threads.append(Thread(index))

    return threads


def get_test_cpu(package_count=DEFAULT_PACKAGE_COUNT, core_count=DEFAULT_CORE_COUNT):
    packages = []
    for p_i in range(package_count):

        cores = []
        for c_i in range(core_count):
            cores.append(Core(__get_threads(p_i, c_i, package_count, core_count)))

        packages.append(Package(cores))

    return Cpu(packages)


class TestCpu(unittest.TestCase):

    def test_assign_one_thread_empty_cpu(self):
        """
        Workload 0: 1 cores --> p:0 c:0 t:0
        """
        cpu = get_test_cpu()
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        w = Workload(uuid.uuid4(), 1)

        assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(cpu.get_empty_threads()))

        threads = get_threads(cpu, w)
        self.assertEqual(1, len(threads))
        self.assertEqual(0, threads[0].get_id())

    def test_assign_two_threads_empty_cpu(self):
        """
        Workload 0: 2 cores --> p:0 c:0 t:[0, 8]
        """
        cpu = get_test_cpu()
        w = Workload(uuid.uuid4(), 2)

        assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 2, len(cpu.get_empty_threads()))

        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        thread8 = core00.get_threads()[1]
        self.assertEqual(8, thread8.get_id())

        # Actual assigned threads
        threads = get_threads(cpu, w)
        self.assertEqual(2, len(threads))
        self.assertEqual(thread0, threads[0])
        self.assertEqual(thread8, threads[1])

    def test_assign_two_workloads_empty_cpu(self):
        """
        Workload 0: 2 cores --> p:0 c:0 t:[0, 8]
        Workload 1: 1 core  --> p:1 c:0 t:[4]
        """
        cpu = get_test_cpu()
        w0 = Workload(uuid.uuid4(), 2)
        w1 = Workload(uuid.uuid4(), 1)

        assign_threads(cpu, w0)
        assign_threads(cpu, w1)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 3, len(cpu.get_empty_threads()))

        # WORKLOAD 0
        # Expected core and threads
        core00 = cpu.get_packages()[0].get_cores()[0]
        thread0 = core00.get_threads()[0]
        self.assertEqual(0, thread0.get_id())
        thread8 = core00.get_threads()[1]
        self.assertEqual(8, thread8.get_id())

        # Actual assigned threads
        threads = get_threads(cpu, w0)
        self.assertEqual(2, len(threads))
        self.assertEqual(thread0, threads[0])
        self.assertEqual(thread8, threads[1])

        # WORKLOAD 1
        # Expected core and threads
        core00 = cpu.get_packages()[1].get_cores()[0]
        thread4 = core00.get_threads()[0]
        self.assertEqual(4, thread4.get_id())

        # Actual assigned threads
        threads = get_threads(cpu, w1)
        self.assertEqual(1, len(threads))
        self.assertEqual(thread4, threads[0])

    def test_assign_ten_threads_empty_cpu(self):
        """
        Workload 0: 10 cores --> p:0 c:[0-3] t:[0-3, 8-11]
                                 p:1 c:0     t:[4, 12]
        """
        cpu = get_test_cpu()
        w = Workload(uuid.uuid4(), 10)

        assign_threads(cpu, w)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 10, len(cpu.get_empty_threads()))

        expected_thread_ids = [0, 1, 2, 3, 4, 8, 9, 10, 11, 12]

        threads = get_threads(cpu, w)
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
        cpu = get_test_cpu()
        w0 = Workload(uuid.uuid4(), 8)
        w1 = Workload(uuid.uuid4(), 4)
        w2 = Workload(uuid.uuid4(), 2)
        w3 = Workload(uuid.uuid4(), 1)
        w4 = Workload(uuid.uuid4(), 1)

        workloads = [w0, w1, w2, w3, w4]
        list(map(lambda w: assign_threads(cpu, w), workloads))

        self.assertEqual(0, len(cpu.get_empty_threads()))
        self.assertEqual(8, len(get_threads(cpu, w0)))
        self.assertEqual(4, len(get_threads(cpu, w1)))
        self.assertEqual(2, len(get_threads(cpu, w2)))
        self.assertEqual(1, len(get_threads(cpu, w3)))
        self.assertEqual(1, len(get_threads(cpu, w4)))

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
        cpu = get_test_cpu()

        # Initialize fragmented workload
        wa = Workload(uuid.uuid4(), 8)

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
        w0 = Workload(uuid.uuid4(), 2)
        w1 = Workload(uuid.uuid4(), 3)
        w2 = Workload(uuid.uuid4(), 1)
        w3 = Workload(uuid.uuid4(), 2)

        workloads = [w0, w1, w2, w3]
        list(map(lambda w: assign_threads(cpu, w), workloads))

        self.assertEqual(0, len(cpu.get_empty_threads()))
