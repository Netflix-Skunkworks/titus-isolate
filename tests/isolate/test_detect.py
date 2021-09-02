import logging
import unittest
import uuid

from tests.utils import config_logs, get_test_workload, get_allocate_request
from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.model.processor.config import get_cpu

config_logs(logging.DEBUG)


class TestDetect(unittest.TestCase):

    def test_no_cross_package_violation(self):
        cpu = get_cpu()
        allocator = GreedyCpuAllocator()
        w = get_test_workload(uuid.uuid4(), 4)

        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

        request = get_allocate_request(cpu, [w])
        cpu = allocator.isolate(request).get_cpu()
        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

    def test_one_cross_package_violation(self):
        cpu = get_cpu()
        allocator = GreedyCpuAllocator()
        w = get_test_workload(uuid.uuid4(), 9)

        request = get_allocate_request(cpu, [w])
        cpu = allocator.isolate(request).get_cpu()
        violations = get_cross_package_violations(cpu)
        self.assertEqual(1, len(violations))

    def test_shared_core_violation(self):
        allocator = GreedyCpuAllocator()

        # Claim all thread but one
        cpu = get_cpu()
        w_0 = get_test_workload(uuid.uuid4(), len(cpu.get_threads()) - 1)
        request = get_allocate_request(cpu, [w_0])
        cpu = allocator.isolate(request).get_cpu()
        log.info("{}".format(cpu))
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(0, len(violations))

        # Assign another workload which will force core sharing
        w_1 = get_test_workload(uuid.uuid4(), 1)
        request = get_allocate_request(cpu, [w_0, w_1])
        cpu = allocator.isolate(request).get_cpu()
        log.info("{}".format(cpu))
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(1, len(violations))
