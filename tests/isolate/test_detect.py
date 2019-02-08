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
        allocator = IntegerProgramCpuAllocator()
        w = Workload(uuid.uuid4(), 4, STATIC)

        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

        cpu = allocator.assign_threads(cpu, w)
        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

    def test_one_cross_package_violation(self):
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator()
        w = Workload(uuid.uuid4(), 9, STATIC)

        cpu = allocator.assign_threads(cpu, w)
        violations = get_cross_package_violations(cpu)
        self.assertEqual(1, len(violations))

    def test_shared_core_violation(self):
        allocator = IntegerProgramCpuAllocator()

        # Claim all thread but one
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), len(cpu.get_threads()) - 1, STATIC)
        cpu = allocator.assign_threads(cpu, w)
        log.info("{}".format(cpu))
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(0, len(violations))

        # Assign another workload which will force core sharing
        w = Workload(uuid.uuid4(), 1, STATIC)
        cpu = allocator.assign_threads(cpu, w)
        log.info("{}".format(cpu))
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(1, len(violations))
