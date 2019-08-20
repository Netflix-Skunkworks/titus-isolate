import logging
import numpy as np
import unittest
import uuid

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs, get_test_workload, get_threads_with_workload, DEFAULT_TEST_REQUEST_METADATA
from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
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
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.cpu_usage_provider import CpuUsageProvider
from titus_isolate.monitor.oversubscribe_free_thread_provider import OversubscribeFreeThreadProvider
from titus_isolate.predict.cpu_usage_predictor import PredEnvironment
from titus_isolate.utils import set_workload_monitor_manager

config_logs(logging.INFO)


class TestPredictor(object):
    
    def __init__(self):
        self.meta_data = {'model_training_titus_task_id': '123'}


class TestCpuUsagePredictor:

    def __init__(self, constant_percent_busy: float = 100):
        self.__constant_percent_busy = constant_percent_busy
        self.__model = TestPredictor()

    def predict(self, workload: Workload, cpu_usage_last_hour: np.array, pred_env: PredEnvironment) -> float:
        return workload.get_thread_count() * self.__constant_percent_busy / 100

    def get_model(self):
        return self.__model


class TestCpuUsagePredictorManager:

    def __init__(self, predictor=TestCpuUsagePredictor()):
        self.__predictor = predictor

    def get_predictor(self):
        return self.__predictor

    def set_predictor(self, predictor):
        self.__predictor = predictor


class TestWorkloadMonitorManager(CpuUsageProvider):

    def __init__(self, cpu_usage={}):
        self.__cpu_usage = cpu_usage

    def get_cpu_usage(self, seconds: int, agg_granularity_secs: int) -> dict:
        return self.__cpu_usage


forecast_ip_alloc_simple = ForecastIPCpuAllocator(
    TestCpuUsagePredictorManager(),
    ConfigManager(TestPropertyProvider({})),
    OversubscribeFreeThreadProvider(0.1))

ALLOCATORS = [NaiveCpuAllocator(), IntegerProgramCpuAllocator(), GreedyCpuAllocator(), forecast_ip_alloc_simple]
OVER_ALLOCATORS = [NaiveCpuAllocator()]

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

            request = AllocateThreadsRequest(cpu, w.get_id(), {w.get_id(): w}, {}, DEFAULT_TEST_REQUEST_METADATA)
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

            request = AllocateThreadsRequest(cpu, w.get_id(), {w.get_id(): w}, {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(2, len(cpu.get_claimed_threads()))

    def test_assign_more_than_available_threads_with_one_workload(self):
        for allocator in OVER_ALLOCATORS:
            cpu = get_cpu()
            w_jumbo = get_test_workload("jumbo", DEFAULT_TOTAL_THREAD_COUNT * 1.5, STATIC)

            request = AllocateThreadsRequest(
                cpu,
                w_jumbo.get_id(),
                {
                    w_jumbo.get_id(): w_jumbo
                },
                {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)

            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))
            self.assertEqual([w_jumbo.get_id()], list(cpu.get_workload_ids_to_thread_ids().keys()))

    def test_assign_more_than_available_threads_with_two_workloads(self):
        for allocator in OVER_ALLOCATORS:
            cpu = get_cpu()
            w_fill = get_test_workload("fill", DEFAULT_TOTAL_THREAD_COUNT, STATIC)
            w_extra = get_test_workload("extra", DEFAULT_TOTAL_THREAD_COUNT * 1.5, STATIC)

            request = AllocateThreadsRequest(
                cpu,
                w_fill.get_id(),
                {
                    w_fill.get_id(): w_fill
                },
                {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request).get_cpu()
            log.info(cpu)
            self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_claimed_threads()))
            self.assertEqual([w_fill.get_id()], list(cpu.get_workload_ids_to_thread_ids().keys()))

            request = AllocateThreadsRequest(
                cpu,
                w_extra.get_id(),
                {
                    w_fill.get_id(): w_fill,
                    w_extra.get_id(): w_extra
                },
                {}, DEFAULT_TEST_REQUEST_METADATA)
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

            request0 = AllocateThreadsRequest(cpu, w0.get_id(), {w0.get_id(): w0}, {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request0).get_cpu()

            request1 = AllocateThreadsRequest(cpu, w1.get_id(),
                                              {
                                                  w0.get_id(): w0,
                                                  w1.get_id(): w1
                                              },
                                              {},
                                              DEFAULT_TEST_REQUEST_METADATA)
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

        request0 = AllocateThreadsRequest(cpu, w0.get_id(), {w0.get_id(): w0}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request0).get_cpu()

        request1 = AllocateThreadsRequest(cpu, w1.get_id(),
                                          {
                                              w0.get_id(): w0,
                                              w1.get_id(): w1
                                          },
                                          {},
                                          DEFAULT_TEST_REQUEST_METADATA)
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

            request = AllocateThreadsRequest(cpu, w.get_id(), {w.get_id(): w}, {}, DEFAULT_TEST_REQUEST_METADATA)
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
            workload_map = {}
            for w in workloads:
                workload_map[w.get_id()] = w
                request = AllocateThreadsRequest(cpu, w.get_id(), workload_map, {}, DEFAULT_TEST_REQUEST_METADATA)
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
        for w in workloads:
            workload_map[w.get_id()] = w
            request = AllocateThreadsRequest(cpu, w.get_id(), workload_map, {}, DEFAULT_TEST_REQUEST_METADATA)
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
            workloads = {
                w.get_id(): w
            }
            request = AllocateThreadsRequest(cpu, w.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
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

            workloads[w0.get_id()] = w0
            request = AllocateThreadsRequest(cpu, w0.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request).get_cpu()

            workloads[w1.get_id()] = w1
            request = AllocateThreadsRequest(cpu, w1.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request).get_cpu()

            workloads[w2.get_id()] = w2
            request = AllocateThreadsRequest(cpu, w2.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.assign_threads(request).get_cpu()
            self.assertEqual(3 + 4 + 2, len(cpu.get_claimed_threads()))

            request = AllocateThreadsRequest(cpu, w1.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
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
        workloads = {}

        workload = get_test_workload("a", 2, STATIC)
        workloads[workload.get_id()] = workload
        request = AllocateThreadsRequest(cpu, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        self.assertEqual(1, len(allocator._IntegerProgramCpuAllocator__cache))

        workload = get_test_workload("b", 2, STATIC)
        workloads[workload.get_id()] = workload
        request = AllocateThreadsRequest(cpu, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        self.assertEqual(2, len(allocator._IntegerProgramCpuAllocator__cache))

        request = AllocateThreadsRequest(cpu, "b", workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.free_threads(request).get_cpu()
        self.assertEqual(3, len(allocator._IntegerProgramCpuAllocator__cache))
        workloads.pop("b")

        workload = get_test_workload("c", 2, STATIC)
        workloads[workload.get_id()] = workload
        request = AllocateThreadsRequest(cpu, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        self.assertEqual(3, len(allocator._IntegerProgramCpuAllocator__cache))

        request = AllocateThreadsRequest(cpu, "a", workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.free_threads(request).get_cpu()
        self.assertEqual(4, len(allocator._IntegerProgramCpuAllocator__cache))
        workloads.pop("a")

        workload = get_test_workload("d", 2, STATIC)
        workloads[workload.get_id()] = workload
        request = AllocateThreadsRequest(cpu, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        allocator.assign_threads(request).get_cpu()
        self.assertEqual(5, len(allocator._IntegerProgramCpuAllocator__cache))

    def test_balance_forecast_ip(self):
        cpu = get_cpu()

        w1 = get_test_workload("a", 2, STATIC)
        w2 = get_test_workload("b", 4, BURST)

        allocator = forecast_ip_alloc_simple

        request = AllocateThreadsRequest(cpu, "a", {"a": w1}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()

        request = AllocateThreadsRequest(cpu, "b", {"a": w1, "b": w2}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()

        request = AllocateRequest(cpu, {"a": w1, "b": w2}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.rebalance(request).get_cpu()

        self.assertLessEqual(2 + 4, len(cpu.get_claimed_threads()))

        w2t = cpu.get_workload_ids_to_thread_ids()
        self.assertEqual(2, len(w2t["a"]))
        self.assertLessEqual(4, len(w2t["b"]))  # burst got at least 4

        for _ in range(20):
            request = AllocateRequest(cpu, {"a": w1, "b": w2}, {}, DEFAULT_TEST_REQUEST_METADATA)
            cpu = allocator.rebalance(request).get_cpu()

        w2t = cpu.get_workload_ids_to_thread_ids()
        self.assertEqual(2, len(w2t["a"]))
        self.assertLessEqual(4, len(w2t["b"]))

    def test_forecast_ip_big_burst_pool_if_empty_instance(self):
        cpu = get_cpu()
        allocator = forecast_ip_alloc_simple

        w = get_test_workload("a", 1, BURST)

        request = AllocateThreadsRequest(cpu, "a", {"a": w}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()

        original_burst_claim_sz = len(cpu.get_claimed_threads())
        # should at least consume all the cores:
        self.assertLessEqual(len(cpu.get_threads()) / 2, original_burst_claim_sz)

        w2 = get_test_workload("b", 3, STATIC)
        request = AllocateThreadsRequest(cpu, "b", {"a": w, "b": w2}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()

        new_burst_claim_sz = len(get_threads_with_workload(cpu, w2.get_id()))
        self.assertLess(new_burst_claim_sz, original_burst_claim_sz)

        total_claim_sz = len(cpu.get_claimed_threads())
        self.assertLessEqual(3 + 1, total_claim_sz)
        self.assertLessEqual(1, new_burst_claim_sz)

        # there shouldn't be an empty core
        for p in cpu.get_packages():
            for c in p.get_cores():
                self.assertLess(0, sum(t.is_claimed() for t in c.get_threads()))

        request = AllocateThreadsRequest(cpu, "b", {"a": w, "b": w2}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.free_threads(request).get_cpu()

        request = AllocateRequest(cpu,  {"a": w}, {}, DEFAULT_TEST_REQUEST_METADATA)
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

        request = AllocateThreadsRequest(cpu, "static_a", {"static_a": w_a}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()

        request = AllocateThreadsRequest(cpu, "burst_c", {"static_a": w_a, "burst_c": w_c}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        # with an aggressive burst pool expansion, burst should be collocated with static on cores:
        self.assertLess(40, len(cpu.get_claimed_threads()))
        num_burst_1 = len(cpu.get_workload_ids_to_thread_ids()["burst_c"])

        request = AllocateThreadsRequest(cpu, "static_b", {"static_a": w_a, "static_b": w_b, "burst_c": w_c}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        # burst should retract, and prefer collocation with b over a:
        num_burst_2 = len(cpu.get_workload_ids_to_thread_ids()["burst_c"])
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
                    if (wt1 == 'static_a' and wt2 == 'burst_c') or (wt1 == 'burst_c' and wt2 == 'static_a'):
                        colloc_a += 1
                    elif (wt1 == 'static_b' and wt2 == 'burst_c') or (wt1 == 'burst_c' and wt2 == 'static_b'):
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

        request = AllocateThreadsRequest(cpu, w0.get_id(), {w0.get_id(): w0}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        log.info(cpu)

        # All cores should be occupied
        for c in cpu.get_cores():
            self.assertEqual(1, len(c.get_empty_threads()))

        w1 = get_test_workload(uuid.uuid4(), thread_count, BURST)
        request = AllocateThreadsRequest(
            cpu,
            w1.get_id(),
            {
                w0.get_id(): w0,
                w1.get_id(): w1
            },
            {},
            DEFAULT_TEST_REQUEST_METADATA)
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

        request = AllocateThreadsRequest(cpu, w0.get_id(), {w0.get_id(): w0}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        log.info(cpu)

        # All cores should be occupied
        for c in cpu.get_cores():
            self.assertTrue(len(c.get_empty_threads()) == 1 or len(c.get_empty_threads()) == 2)

        w1 = get_test_workload("b", thread_count, BURST)
        log.info(w1)
        request = AllocateThreadsRequest(
            cpu,
            w1.get_id(),
            {
                w0.get_id(): w0,
                w1.get_id(): w1
            },
            {},
            DEFAULT_TEST_REQUEST_METADATA)
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
