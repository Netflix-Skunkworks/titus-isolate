import logging
import unittest
import uuid

from tests.utils import config_logs
from titus_isolate import log
from titus_isolate.docker.constants import STATIC
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload

config_logs(logging.DEBUG)


class TestDetect(unittest.TestCase):

    def test_no_cross_package_violation(self):
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)
        w = Workload(uuid.uuid4(), 4, STATIC)

        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

        allocator.assign_threads(w)
        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

    def test_one_cross_package_violation(self):
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator(cpu)
        w = Workload(uuid.uuid4(), 9, STATIC)

        allocator.assign_threads(w)
        violations = get_cross_package_violations(cpu)
        self.assertEqual(1, len(violations))

    def test_shared_core_violation(self):
        cpu = get_cpu()
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(0, len(violations))

        # Claim 1 thread on every core
        dummy_workload_id = uuid.uuid4()
        for p in cpu.get_packages():
            for c in p.get_cores():
                c.get_threads()[0].claim(dummy_workload_id)

        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(0, len(violations))

        # Assign another workload which will force core sharing
        allocator = IntegerProgramCpuAllocator(cpu)
        w = Workload(uuid.uuid4(), 2, STATIC)
        allocator.assign_threads(w)
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(2, len(violations))
