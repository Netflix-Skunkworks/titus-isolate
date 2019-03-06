import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate.event.constants import BURST
from titus_isolate.isolate.update import get_updates
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT

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
        self.assertEqual(1, len(updates))
        self.assertEqual(updates[workload_id], [0])

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
        self.assertEqual(1, len(updates))
        self.assertEqual(updates[workload_id], [8])
