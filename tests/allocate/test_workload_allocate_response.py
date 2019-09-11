import unittest

from tests.utils import get_test_workload, get_test_opportunistic_workload
from titus_isolate.allocate.workload_allocate_response import get_workload_response
from titus_isolate.config.constants import DEFAULT_QUOTA_SCALE, DEFAULT_SHARES_SCALE, DEFAULT_OPPORTUNISTIC_SHARES_SCALE
from titus_isolate.event.constants import STATIC, BURST
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload


def assign_threads(workload: Workload) -> Cpu:
    cpu = get_cpu()
    threads = cpu.get_threads()

    total_thread_count = workload.get_thread_count() + workload.get_opportunistic_thread_count()
    for i in range(total_thread_count):
        threads[i].claim(workload.get_id())

    return cpu


class TestWorkloadAllocateReponse(unittest.TestCase):

    def test_static_normal_construction(self):
        thread_count = 2
        w = get_test_workload("a", thread_count, STATIC)
        cpu = assign_threads(w)

        w_resp = get_workload_response(w, cpu)
        self.assertEqual(thread_count, len(w_resp.get_thread_ids()))

        expected_quota = thread_count * DEFAULT_QUOTA_SCALE
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())

    def test_static_oversubscription_construction(self):
        thread_count = 2
        opportunistic_thread_count = 4
        w = get_test_opportunistic_workload("a", thread_count, opportunistic_thread_count, STATIC)
        cpu = assign_threads(w)

        w_resp = get_workload_response(w, cpu)
        self.assertEqual(thread_count + opportunistic_thread_count, len(w_resp.get_thread_ids()))

        expected_quota = thread_count * DEFAULT_QUOTA_SCALE
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_OPPORTUNISTIC_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())

    def test_burst_normal_construction(self):
        thread_count = 2
        w = get_test_workload("a", thread_count, BURST)
        cpu = assign_threads(w)

        w_resp = get_workload_response(w, cpu)
        self.assertEqual(thread_count, len(w_resp.get_thread_ids()))

        expected_quota = -1
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())

    def test_burst_oversubscription_construction(self):
        thread_count = 2
        opportunistic_thread_count = 4
        w = get_test_opportunistic_workload("a", thread_count, opportunistic_thread_count, BURST)
        cpu = assign_threads(w)

        w_resp = get_workload_response(w, cpu)
        self.assertEqual(thread_count + opportunistic_thread_count, len(w_resp.get_thread_ids()))

        expected_quota = -1
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_OPPORTUNISTIC_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())
