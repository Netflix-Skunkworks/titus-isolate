import logging
from typing import Optional

import unittest
import uuid

from kubernetes.client import V1Pod

from tests.utils import config_logs, get_test_workload, get_no_usage_threads_request, TestWorkloadMonitorManager
from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.utils import set_workload_monitor_manager

config_logs(logging.INFO)


class TestPodManager:
    def __init__(self):
        self.pod = None

    def set_pod(self, pod: V1Pod):
        self.pod = pod

    def get_pod(self, pod_name: str) -> Optional[V1Pod]:
        return self.pod


ALLOCATORS = [NaiveCpuAllocator(), GreedyCpuAllocator()]
OVER_ALLOCATORS = [NaiveCpuAllocator()]

set_workload_monitor_manager(TestWorkloadMonitorManager())


class TestAllocation(unittest.TestCase):

    def test_assign_one_thread_empty_cpu(self):
        """
        Workload 0: 1 thread --> (p:0 c:0 t:0)
        """
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

            w = get_test_workload(uuid.uuid4(), 1)

            request = get_no_usage_threads_request(cpu, [w])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(cpu.get_empty_threads()))
            self.assertEqual(1, len(cpu.get_claimed_threads()))
            self.assertEqual(w.get_task_id(), cpu.get_claimed_threads()[0].get_workload_ids()[0])

    def test_assign_two_threads_empty_cpu_ip(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        """
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            w = get_test_workload(uuid.uuid4(), 2)

            request = get_no_usage_threads_request(cpu, [w])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(2, len(cpu.get_claimed_threads()))

    def test_assign_more_than_available_threads_with_two_workloads(self):
        for allocator in OVER_ALLOCATORS:
            cpu = get_cpu()
            w_fill = get_test_workload("fill", DEFAULT_TOTAL_THREAD_COUNT)
            w_extra = get_test_workload("extra", DEFAULT_TOTAL_THREAD_COUNT * 1)

            request = get_no_usage_threads_request(cpu, [w_fill])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))
            self.assertEqual([w_fill.get_task_id()], list(cpu.get_workload_ids_to_thread_ids().keys()))

            request = get_no_usage_threads_request(cpu, [w_fill, w_extra])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))
            self.assertEqual(
                sorted([w_fill.get_task_id(), w_extra.get_task_id()]),
                sorted(list(cpu.get_workload_ids_to_thread_ids().keys())))

    def test_assign_two_workloads_empty_cpu_greedy(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:0 t:1)
        Workload 1: 1 thread  --> (p:1 c:0 t:0)
        """
        cpu = get_cpu()
        allocator = GreedyCpuAllocator()
        w0 = get_test_workload(uuid.uuid4(), 2)
        w1 = get_test_workload(uuid.uuid4(), 1)

        request0 = get_no_usage_threads_request(cpu, [w0])
        cpu = allocator.assign_threads(request0).get_cpu()

        request1 = get_no_usage_threads_request(cpu, [w0, w1])
        cpu = allocator.assign_threads(request1).get_cpu()

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
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            workloads = [
                get_test_workload("v", 8),
                get_test_workload("w", 4),
                get_test_workload("x", 2),
                get_test_workload("y", 1),
                get_test_workload("z", 1)]

            tot_req = 0
            __workloads = []
            for w in workloads:
                __workloads.append(w)
                request = get_no_usage_threads_request(cpu, __workloads)
                cpu = allocator.assign_threads(request).get_cpu()
                log.info(cpu)
                tot_req += w.get_thread_count()
                self.assertEqual(tot_req, len(cpu.get_claimed_threads()))

    def test_free_cpu(self):
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

            w = get_test_workload(uuid.uuid4(), 3)
            request = get_no_usage_threads_request(cpu, [w])
            cpu = allocator.assign_threads(request).get_cpu()
            self.assertEqual(
                DEFAULT_TOTAL_THREAD_COUNT - w.get_thread_count(),
                len(cpu.get_empty_threads()))

            cpu = allocator.free_threads(request).get_cpu()
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

    def test_free_cpu_3_workloads(self):
        # Add 3 workloads sequentially, and then remove the 2nd one added.
        for allocator in ALLOCATORS:
            cpu = get_cpu()

            w0 = get_test_workload(123, 3)
            w1 = get_test_workload(456, 2)
            w2 = get_test_workload(789, 4)

            request = get_no_usage_threads_request(cpu, [w0])
            cpu = allocator.assign_threads(request).get_cpu()

            request = get_no_usage_threads_request(cpu, [w0, w1])
            cpu = allocator.assign_threads(request).get_cpu()

            request = get_no_usage_threads_request(cpu, [w0, w1, w2])
            cpu = allocator.assign_threads(request).get_cpu()
            self.assertEqual(3 + 4 + 2, len(cpu.get_claimed_threads()))

            request = get_no_usage_threads_request(cpu, [w0, w2, w1])
            cpu = allocator.free_threads(request).get_cpu()
            self.assertEqual(3 + 4, len(cpu.get_claimed_threads()))

            workload_ids_left = set()
            for t in cpu.get_threads():
                if t.is_claimed():
                    for w_id in t.get_workload_ids():
                        workload_ids_left.add(w_id)

            self.assertListEqual(sorted(list(workload_ids_left)), [123, 789])
