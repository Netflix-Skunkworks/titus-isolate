import unittest

from tests.utils import get_test_workload, get_test_opportunistic_workload
from titus_isolate.allocate.workload_allocate_response import WorkloadAllocateResponse
from titus_isolate.config.constants import DEFAULT_QUOTA_SCALE, DEFAULT_SHARES_SCALE, DEFAULT_OPPORTUNISTIC_SHARES_SCALE
from titus_isolate.event.constants import STATIC, BURST


class TestWorkloadAllocateReponse(unittest.TestCase):

    def test_static_normal_construction(self):
        thread_count = 2
        expected_thread_ids = [1, 8]
        w = get_test_workload("a", thread_count, STATIC)

        w_resp = WorkloadAllocateResponse(w, expected_thread_ids)
        self.assertEqual(w, w_resp.get_workload())
        self.assertEqual(expected_thread_ids, w_resp.get_thread_ids())

        expected_quota = thread_count * DEFAULT_QUOTA_SCALE
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())

    def test_static_oversubscription_construction(self):
        thread_count = 2
        opportunistic_thread_count = 4
        expected_thread_ids = [1, 8, 7, 3, 2, 4]
        w = get_test_opportunistic_workload("a", thread_count, opportunistic_thread_count, STATIC)

        w_resp = WorkloadAllocateResponse(w, expected_thread_ids)
        self.assertEqual(w, w_resp.get_workload())
        self.assertEqual(expected_thread_ids, w_resp.get_thread_ids())

        expected_quota = thread_count * DEFAULT_QUOTA_SCALE
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_OPPORTUNISTIC_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())

    def test_burst_normal_construction(self):
        thread_count = 2
        expected_thread_ids = [1, 8]
        w = get_test_workload("a", thread_count, BURST)

        w_resp = WorkloadAllocateResponse(w, expected_thread_ids)
        self.assertEqual(w, w_resp.get_workload())
        self.assertEqual(expected_thread_ids, w_resp.get_thread_ids())

        expected_quota = -1
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())

    def test_burst_oversubscription_construction(self):
        thread_count = 2
        opportunistic_thread_count = 4
        expected_thread_ids = [1, 8, 7, 3, 2, 4]
        w = get_test_opportunistic_workload("a", thread_count, opportunistic_thread_count, BURST)

        w_resp = WorkloadAllocateResponse(w, expected_thread_ids)
        self.assertEqual(w, w_resp.get_workload())
        self.assertEqual(expected_thread_ids, w_resp.get_thread_ids())

        expected_quota = -1
        self.assertEqual(expected_quota, w_resp.get_cpu_quota())

        expected_shares = thread_count * DEFAULT_OPPORTUNISTIC_SHARES_SCALE
        self.assertEqual(expected_shares, w_resp.get_cpu_shares())
