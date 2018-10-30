import logging
import unittest
import uuid

from titus_isolate.docker.constants import BURST
from titus_isolate.isolate.update import get_updates
from titus_isolate.model.processor.utils import get_cpu, DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)


class TestUpdate(unittest.TestCase):

    def test_get_updates_single_new_workload(self):
        workload_id = str(uuid.uuid4())

        # Empty CPU to start
        cur_cpu = get_cpu()

        # Assign a workload to thread 0 on the new CPU
        new_cpu = get_cpu()
        new_cpu.get_threads()[0].claim(workload_id)

        updates = get_updates(cur_cpu, new_cpu)
        self.assertEqual(2, len(updates))
        self.assertEqual(updates[workload_id], [0])
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(updates[BURST]))

    def test_no_updates_single_new_workload(self):
        workload_id = str(uuid.uuid4())

        cur_cpu = get_cpu()
        new_cpu = get_cpu()

        # Assign a workload to thread 0 on both CPUs
        cur_cpu.get_threads()[0].claim(workload_id)
        new_cpu.get_threads()[0].claim(workload_id)

        updates = get_updates(cur_cpu, new_cpu)
        self.assertEqual(0, len(updates))

    def test_get_updates_single_moved_workload(self):
        workload_id = str(uuid.uuid4())

        cur_cpu = get_cpu()
        new_cpu = get_cpu()

        # Migrate from thread 0 to thread 1 (processor_id 8)
        cur_cpu.get_threads()[0].claim(workload_id)
        new_cpu.get_threads()[1].claim(workload_id)

        updates = get_updates(cur_cpu, new_cpu)
        self.assertEqual(2, len(updates))
        self.assertEqual(updates[workload_id], [8])
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - 1, len(updates[BURST]))

    def test_burst_footprint_increase(self):
        workload_id = str(uuid.uuid4())

        cur_cpu = get_cpu()
        new_cpu = get_cpu()

        cur_cpu.get_threads()[0].claim(workload_id)
        updates = get_updates(cur_cpu, new_cpu)
        self.assertEqual(1, len(updates))
        self.assertTrue(BURST in updates)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(updates[BURST]))
