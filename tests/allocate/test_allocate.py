import logging
from typing import Optional

import numpy as np
import unittest
import uuid

from kubernetes.client import V1Pod

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, get_test_workload, get_threads_with_workload, get_no_usage_threads_request, \
    get_no_usage_rebalance_request, TestCpuUsagePredictorManager, TestPredictor, TestCpuUsagePredictor
from titus_isolate import log
from titus_isolate.allocate.forecast_ip_cpu_allocator import ForecastIPCpuAllocator
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.event.constants import BURST
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import BURST_CORE_COLLOC_USAGE_THRESH
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.oversubscribe_free_thread_provider import OversubscribeFreeThreadProvider
from titus_isolate.predict.cpu_usage_predictor import PredEnvironment
from titus_isolate.utils import set_workload_monitor_manager

config_logs(logging.INFO)


class TestWorkloadMonitorManager:

    @staticmethod
    def get_pcp_usage() -> dict:
        return {}


class TestPodManager:
    def __init__(self):
        self.pod = None

    def set_pod(self, pod: V1Pod):
        self.pod = pod

    def get_pod(self, pod_name: str) -> Optional[V1Pod]:
        return self.pod


forecast_ip_alloc_simple = ForecastIPCpuAllocator(
    TestCpuUsagePredictorManager(),
    ConfigManager(TestPropertyProvider({})),
    OversubscribeFreeThreadProvider(0.1))

ALLOCATORS = [NaiveCpuAllocator(), IntegerProgramCpuAllocator(), GreedyCpuAllocator(), forecast_ip_alloc_simple]
OVER_ALLOCATORS = [NaiveCpuAllocator(), forecast_ip_alloc_simple]

set_workload_monitor_manager(TestWorkloadMonitorManager())


class TestCpu(unittest.TestCase):

    def test_assign_one_thread_empty_cpu(self):
        """
        Workload 0: 1 thread --> (p:0 c:0 t:0)
        """
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

            w = get_test_workload(uuid.uuid4(), 1, STATIC)

            request = get_no_usage_threads_request(cpu, [w])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(cpu.get_empty_threads()))
            self.assertEqual(1, len(cpu.get_claimed_threads()))
            self.assertEqual(w.get_id(), cpu.get_claimed_threads()[0].get_workload_ids()[0])

    def test_assign_two_threads_empty_cpu_ip(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        """
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            w = get_test_workload(uuid.uuid4(), 2, STATIC)

            request = get_no_usage_threads_request(cpu, [w])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(2, len(cpu.get_claimed_threads()))

    def test_assign_more_than_available_threads_with_two_workloads(self):
        for allocator in OVER_ALLOCATORS:
            cpu = get_cpu()
            w_fill = get_test_workload("fill", DEFAULT_TOTAL_THREAD_COUNT, STATIC)
            w_extra = get_test_workload("extra", DEFAULT_TOTAL_THREAD_COUNT * 1, STATIC)

            request = get_no_usage_threads_request(cpu, [w_fill])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))
            self.assertEqual([w_fill.get_id()], list(cpu.get_workload_ids_to_thread_ids().keys()))

            request = get_no_usage_threads_request(cpu, [w_fill, w_extra])
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))
            self.assertEqual(
                sorted([w_fill.get_id(), w_extra.get_id()]),
                sorted(list(cpu.get_workload_ids_to_thread_ids().keys())))

    def test_assign_two_workloads_empty_cpu_ip(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:1 t:0)
        Workload 1: 1 thread  --> (p:1 c:0 t:0)
        """
        for allocator in [IntegerProgramCpuAllocator(), forecast_ip_alloc_simple]:
            cpu = get_cpu()
            w0 = get_test_workload(uuid.uuid4(), 2, STATIC)
            w1 = get_test_workload(uuid.uuid4(), 1, STATIC)

            request0 = get_no_usage_threads_request(cpu, [w0])
            cpu = allocator.assign_threads(request0).get_cpu()

            request1 = get_no_usage_threads_request(cpu, [w0, w1])
            cpu = allocator.assign_threads(request1).get_cpu()

            self.assertEqual(3, len(cpu.get_claimed_threads()))

            ids_per_socket = []
            for pid, p in enumerate(cpu.get_packages()):
                r = []
                for cid, c in enumerate(p.get_cores()):
                    for tid, t in enumerate(c.get_threads()):
                        if t.is_claimed():
                            self.assertEqual(1, len(t.get_workload_ids()))
                            r.append((t.get_workload_ids()[0], c.get_id()))
                ids_per_socket.append(r)

            for r in ids_per_socket:
                # each workload should be on a different socket
                self.assertEqual(1, len(set([e[0] for e in r])))
                # assigned threads should be on different coreds
                core_ids = [e[1] for e in r]
                self.assertEqual(len(set(core_ids)), len(core_ids))

    def test_assign_two_workloads_empty_cpu_greedy(self):
        """
        Workload 0: 2 threads --> (p:0 c:0 t:0) (p:0 c:0 t:1)
        Workload 1: 1 thread  --> (p:1 c:0 t:0)
        """
        cpu = get_cpu()
        allocator = GreedyCpuAllocator()
        w0 = get_test_workload(uuid.uuid4(), 2, STATIC)
        w1 = get_test_workload(uuid.uuid4(), 1, STATIC)

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

    def test_assign_ten_threads_empty_cpu_ip(self):
        """
        Workload 0: 10 threads --> (p:0 c:[0-7] t:[0-9])
        | 1 | 1 | 1 | 1 |
        | 1 | 1 |   |   |
        | ------------- |
        | 1 | 1 | 1 | 1 |
        |   |   |   |   |
        """
        for allocator in [IntegerProgramCpuAllocator(), forecast_ip_alloc_simple]:
            cpu = get_cpu()
            w = get_test_workload(uuid.uuid4(), 10, STATIC)

            request = get_no_usage_threads_request(cpu, [w])
            cpu = allocator.assign_threads(request).get_cpu()
            self.assertEqual(10, len(cpu.get_claimed_threads()))

            threads_per_socket = []
            for p in cpu.get_packages():
                ths = []
                for c in p.get_cores():
                    for t in c.get_threads():
                        if t.is_claimed():
                            ths.append(t)
                threads_per_socket.append(len(ths))

            self.assertEqual(5, threads_per_socket[0])
            self.assertEqual(5, threads_per_socket[1])

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
                get_test_workload("v", 8, STATIC),
                get_test_workload("w", 4, STATIC),
                get_test_workload("x", 2, STATIC),
                get_test_workload("y", 1, STATIC),
                get_test_workload("z", 1, STATIC)]

            tot_req = 0
            __workloads = []
            for w in workloads:
                __workloads.append(w)
                request = get_no_usage_threads_request(cpu, __workloads)
                cpu = allocator.assign_threads(request).get_cpu()
                log.info(cpu)
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
        allocator = IntegerProgramCpuAllocator()

        # Initialize fragmented workload
        wa = get_test_workload(uuid.uuid4(), 8, STATIC)

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
        w0 = get_test_workload(uuid.uuid4(), 2, STATIC)
        w1 = get_test_workload(uuid.uuid4(), 3, STATIC)
        w2 = get_test_workload(uuid.uuid4(), 1, STATIC)
        w3 = get_test_workload(uuid.uuid4(), 2, STATIC)

        workload_map = {
            wa.get_id(): wa
        }
        workloads = [w0, w1, w2, w3]
        __workloads = [wa]
        for w in workloads:
            __workloads.append(w)
            workload_map[w.get_id()] = w
            request = get_no_usage_threads_request(cpu, __workloads)
            cpu = allocator.assign_threads(request).get_cpu()

        self.assertEqual(0, len(cpu.get_empty_threads()))

        # first workload should be filling completely a socket to avoid cross-socket job layout
        for package in cpu.get_packages():
            if package.get_cores()[0].get_threads()[0].get_workload_ids() != wa.get_id():
                continue
            ids = [t.get_workload_ids() for core in package.get_cores() for t in core.get_threads()]
            self.assertListEqual(ids, [wa.get_id()] * 8)

    def test_free_cpu(self):
        for allocator in ALLOCATORS:
            cpu = get_cpu()
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

            w = get_test_workload(uuid.uuid4(), 3, STATIC)
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

            workloads = {}
            w0 = get_test_workload(123, 3, STATIC)
            w1 = get_test_workload(456, 2, STATIC)
            w2 = get_test_workload(789, 4, STATIC)

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
        allocator = IntegerProgramCpuAllocator()

        w_a = get_test_workload("a", 2, STATIC)
        w_b = get_test_workload("b", 2, STATIC)
        w_c = get_test_workload("c", 2, STATIC)
        w_d = get_test_workload("d", 2, STATIC)

        workloads = [w_a]
        request = get_no_usage_threads_request(cpu, workloads)
        cpu = allocator.assign_threads(request).get_cpu()
        self.assertEqual(1, len(allocator._IntegerProgramCpuAllocator__cache))

        workloads = [w_a, w_b]
        request = get_no_usage_threads_request(cpu, workloads)
        allocator.assign_threads(request).get_cpu()
        self.assertEqual(2, len(allocator._IntegerProgramCpuAllocator__cache))

        cpu = allocator.free_threads(request).get_cpu()
        self.assertEqual(3, len(allocator._IntegerProgramCpuAllocator__cache))

        workloads = [w_a, w_c]
        request = get_no_usage_threads_request(cpu, workloads)
        cpu = allocator.assign_threads(request).get_cpu()
        self.assertEqual(3, len(allocator._IntegerProgramCpuAllocator__cache))

        workloads = [w_c, w_a]
        request = get_no_usage_threads_request(cpu, workloads)
        cpu = allocator.free_threads(request).get_cpu()
        self.assertEqual(4, len(allocator._IntegerProgramCpuAllocator__cache))

        workloads = [w_c, w_d]
        request = get_no_usage_threads_request(cpu, workloads)
        allocator.assign_threads(request).get_cpu()
        self.assertEqual(5, len(allocator._IntegerProgramCpuAllocator__cache))

    def test_balance_forecast_ip(self):
        allocator = forecast_ip_alloc_simple
        cpu = get_cpu()

        w_a = get_test_workload("a", 2, STATIC)
        w_b = get_test_workload("b", 4, BURST)

        workloads = [w_a]
        request = get_no_usage_threads_request(cpu, workloads)
        cpu = allocator.assign_threads(request).get_cpu()

        workloads = [w_a, w_b]
        request = get_no_usage_threads_request(cpu, workloads)
        cpu = allocator.assign_threads(request).get_cpu()

        request = get_no_usage_rebalance_request(cpu, workloads)
        cpu = allocator.rebalance(request).get_cpu()

        self.assertLessEqual(2 + 4, len(cpu.get_claimed_threads()))

        w2t = cpu.get_workload_ids_to_thread_ids()
        self.assertEqual(2, len(w2t["a"]))
        self.assertLessEqual(4, len(w2t["b"]))  # burst got at least 4

        for _ in range(20):
            request = get_no_usage_rebalance_request(cpu, workloads)
            cpu = allocator.rebalance(request).get_cpu()

        w2t = cpu.get_workload_ids_to_thread_ids()
        self.assertEqual(2, len(w2t["a"]))
        self.assertLessEqual(4, len(w2t["b"]))

    def test_forecast_ip_big_burst_pool_if_empty_instance(self):
        cpu = get_cpu()
        allocator = forecast_ip_alloc_simple

        w_a = get_test_workload("a", 1, BURST)
        w_b = get_test_workload("b", 3, STATIC)

        request = get_no_usage_threads_request(cpu, [w_a])
        cpu = allocator.assign_threads(request).get_cpu()

        original_burst_claim_sz = len(cpu.get_claimed_threads())
        # should at least consume all the cores:
        self.assertLessEqual(len(cpu.get_threads()) / 2, original_burst_claim_sz)

        request = get_no_usage_threads_request(cpu, [w_a, w_b])
        cpu = allocator.assign_threads(request).get_cpu()

        new_burst_claim_sz = len(get_threads_with_workload(cpu, w_b.get_id()))
        self.assertLess(new_burst_claim_sz, original_burst_claim_sz)

        total_claim_sz = len(cpu.get_claimed_threads())
        self.assertLessEqual(3 + 1, total_claim_sz)
        self.assertLessEqual(1, new_burst_claim_sz)

        # there shouldn't be an empty core
        for p in cpu.get_packages():
            for c in p.get_cores():
                self.assertLess(0, sum(t.is_claimed() for t in c.get_threads()))

        request = get_no_usage_threads_request(cpu, [w_a, w_b])
        cpu = allocator.free_threads(request).get_cpu()

        request = get_no_usage_threads_request(cpu, [w_a])
        cpu = allocator.rebalance(request).get_cpu()
        self.assertEqual(original_burst_claim_sz, len(cpu.get_claimed_threads()))

    def test_forecast_ip_burst_pool_with_usage(self):
        class UsagePredictorWithBurst:
            def __init__(self):
                self.__model = TestPredictor()

            def predict(self, workload: Workload, cpu_usage_last_hour: np.array, pred_env: PredEnvironment) -> float:
                if workload.get_id() == 'static_a':
                    return workload.get_thread_count() * 0.8
                elif workload.get_id() == 'static_b':
                    return workload.get_thread_count() * 0.01
                elif workload.get_id() == 'burst_c':
                    return workload.get_thread_count() * 0.9

            def get_model(self):
                return self.__model

        upm = TestCpuUsagePredictorManager(UsagePredictorWithBurst())
        cm = ConfigManager(TestPropertyProvider({BURST_CORE_COLLOC_USAGE_THRESH: 0.9}))
        allocator = ForecastIPCpuAllocator(upm, cm, OversubscribeFreeThreadProvider(0.1))

        cpu = get_cpu(package_count=2, cores_per_package=16)
        w_a = get_test_workload("static_a", 14, STATIC)
        w_b = get_test_workload("static_b", 14, STATIC)
        w_c = get_test_workload("burst_c", 2, BURST)

        request = get_no_usage_threads_request(cpu, [w_a])
        cpu = allocator.assign_threads(request).get_cpu()

        request = get_no_usage_threads_request(cpu, [w_a, w_c])
        cpu = allocator.assign_threads(request).get_cpu()
        # with an aggressive burst pool expansion, burst should be collocated with static on cores:
        self.assertLess(40, len(cpu.get_claimed_threads()))
        num_burst_1 = len(cpu.get_workload_ids_to_thread_ids()[w_c.get_id()])

        request = get_no_usage_threads_request(cpu, [w_a, w_c, w_b])
        cpu = allocator.assign_threads(request).get_cpu()
        # burst should retract, and prefer collocation with b over a:
        num_burst_2 = len(cpu.get_workload_ids_to_thread_ids()[w_c.get_id()])
        self.assertLessEqual(num_burst_2, num_burst_1)

        colloc_a = 0
        colloc_b = 0
        for p in cpu.get_packages():
            for c in p.get_cores():
                t1 = c.get_threads()[0]
                t2 = c.get_threads()[1]
                if t1.is_claimed() and t2.is_claimed():
                    wt1 = t1.get_workload_ids()[0]
                    wt2 = t2.get_workload_ids()[0]
                    if (wt1 == w_a.get_id() and wt2 == w_c.get_id()) or (wt1 == w_c.get_id() and wt2 == w_a.get_id()):
                        colloc_a += 1
                    elif (wt1 == w_b.get_id() and wt2 == w_c.get_id()) or (wt1 == w_c.get_id() and wt2 == w_b.get_id()):
                        colloc_b += 1
        self.assertLessEqual(colloc_a, colloc_b)

    def test_forecast_threshold_no_usage(self):
        allocator = ForecastIPCpuAllocator(
            TestCpuUsagePredictorManager(),
            ConfigManager(TestPropertyProvider({})),
            OversubscribeFreeThreadProvider(0.1))

        thread_count = DEFAULT_TOTAL_THREAD_COUNT / 2
        cpu = get_cpu()

        w0 = get_test_workload(uuid.uuid4(), thread_count, STATIC)

        request = get_no_usage_threads_request(cpu, [w0])
        cpu = allocator.assign_threads(request).get_cpu()
        log.info(cpu)

        # All cores should be occupied
        for c in cpu.get_cores():
            self.assertEqual(1, len(c.get_empty_threads()))

        w1 = get_test_workload(uuid.uuid4(), thread_count, BURST)
        request = get_no_usage_threads_request(cpu, [w0, w1])
        cpu = allocator.assign_threads(request).get_cpu()
        log.info(cpu)

        # No threads should be shared
        for c in cpu.get_cores():
            self.assertEqual(c.get_threads()[0].get_workload_ids(), c.get_threads()[1].get_workload_ids())

    def test_forecast_threshold_usage(self):
        allocator = ForecastIPCpuAllocator(
            TestCpuUsagePredictorManager(TestCpuUsagePredictor(10)),
            ConfigManager(TestPropertyProvider({})),
            OversubscribeFreeThreadProvider(0.05))

        thread_count = DEFAULT_TOTAL_THREAD_COUNT / 4
        cpu = get_cpu()

        w0 = get_test_workload("s", thread_count, STATIC)
        log.info(w0)

        request = get_no_usage_threads_request(cpu, [w0])
        cpu = allocator.assign_threads(request).get_cpu()
        log.info(cpu)

        # All cores should be occupied
        for c in cpu.get_cores():
            self.assertTrue(len(c.get_empty_threads()) == 1 or len(c.get_empty_threads()) == 2)

        w1 = get_test_workload("b", thread_count, BURST)
        log.info(w1)
        request = get_no_usage_threads_request(cpu, [w0, w1])
        cpu = allocator.assign_threads(request).get_cpu()
        log.info(cpu)

        for c in cpu.get_cores():
            # Static workload should have unshared cores
            if len(c.get_empty_threads()) == 1:
                for t in c.get_threads():
                    if t.is_claimed():
                        self.assertEqual([w0.get_id()], t.get_workload_ids())
            # Burst workload should have shared cores only with itself
            if len(c.get_empty_threads()) == 0:
                self.assertEqual(c.get_threads()[0].get_workload_ids(), c.get_threads()[1].get_workload_ids())
                self.assertEqual([w1.get_id()], c.get_threads()[1].get_workload_ids())
