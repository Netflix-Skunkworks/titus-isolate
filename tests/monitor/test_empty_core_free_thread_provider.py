import unittest

from titus_isolate.model.processor.config import get_cpu
from titus_isolate.monitor.empty_core_free_thread_provider import EmptyCoreFreeThreadProvider


class TestEmptyCoreFreeThreadProvider(unittest.TestCase):

    def test_all_empty_cores(self):
        cpu = get_cpu()
        p = EmptyCoreFreeThreadProvider()
        free_threads = p.get_free_threads(cpu, {}, {})
        self.assertEqual(len(cpu.get_threads()), len(free_threads))

    def test_all_full_cores(self):
        cpu = get_cpu()
        for c in cpu.get_cores():
            # Claim the first thread of each core
            c.get_threads()[0].claim("a")

        p = EmptyCoreFreeThreadProvider()
        free_threads = p.get_free_threads(cpu, {}, {})
        self.assertEqual(0, len(free_threads))

    def test_one_full_core(self):
        cpu = get_cpu()
        # Claim the first thread
        cpu.get_threads()[0].claim("a")

        p = EmptyCoreFreeThreadProvider()
        free_threads = p.get_free_threads(cpu, {}, {})
        self.assertEqual(len(cpu.get_threads()) - 2, len(free_threads))
