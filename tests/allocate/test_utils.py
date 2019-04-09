import unittest

from tests.utils import get_test_workload
from titus_isolate.allocate.utils import is_burst_core
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.thread import Thread


class TestUtils(unittest.TestCase):

    def test_empty_core_is_burst_core(self):
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])
        self.assertTrue(is_burst_core(core, {}))

    def test_single_burst_workload_is_burst_core(self):
        w = get_test_workload("a", 2, BURST)
        w_map = {w.get_id(): w}

        # First thread is BURST, other is unclaimed
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])

        t0.claim(w.get_id())
        self.assertTrue(is_burst_core(core, w_map))

        # Second thread is BURST, other is unclaimed
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])

        t1.claim(w.get_id())
        self.assertTrue(is_burst_core(core, w_map))

    def test_single_static_workload_is_not_burst_core(self):
        w = get_test_workload("a", 2, STATIC)
        w_map = {w.get_id(): w}

        # First thread is STATIC, other is unclaimed
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])

        t0.claim(w.get_id())
        self.assertFalse(is_burst_core(core, w_map))

        # Second thread is STATIC, other is unclaimed
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])

        t1.claim(w.get_id())
        self.assertFalse(is_burst_core(core, w_map))

    def test_mixed_workloads_is_not_burst_core(self):
        w_static = get_test_workload("a", 2, STATIC)
        w_burst = get_test_workload("b", 2, BURST)
        w_map = {
            w_static.get_id(): w_static,
            w_burst.get_id(): w_burst
        }

        # First thread is STATIC, other is BURST
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])

        t0.claim(w_static.get_id())
        t1.claim(w_burst.get_id())
        self.assertFalse(is_burst_core(core, w_map))

        # Second thread is STATIC, other is BURST
        t0 = Thread(0)
        t1 = Thread(32)
        core = Core(0, [t0, t1])

        t0.claim(w_burst.get_id())
        t1.claim(w_static.get_id())
        self.assertFalse(is_burst_core(core, w_map))
