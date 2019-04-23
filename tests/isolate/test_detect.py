import logging
import unittest
import uuid

from tests.utils import config_logs, get_test_workload, DEFAULT_TEST_REQUEST_METADATA
from titus_isolate import log
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.event.constants import STATIC
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.model.processor.config import get_cpu

config_logs(logging.DEBUG)


class TestDetect(unittest.TestCase):

    def test_no_cross_package_violation(self):
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator()
        w = get_test_workload(uuid.uuid4(), 4, STATIC)

        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

        request = AllocateThreadsRequest(cpu, w.get_id(), {w.get_id(): w}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        violations = get_cross_package_violations(cpu)
        self.assertEqual(0, len(violations))

    def test_one_cross_package_violation(self):
        cpu = get_cpu()
        allocator = IntegerProgramCpuAllocator()
        w = get_test_workload(uuid.uuid4(), 9, STATIC)

        request = AllocateThreadsRequest(cpu, w.get_id(), {w.get_id(): w}, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        violations = get_cross_package_violations(cpu)
        self.assertEqual(1, len(violations))

    def test_shared_core_violation(self):
        allocator = IntegerProgramCpuAllocator()

        # Claim all thread but one
        cpu = get_cpu()
        w = get_test_workload(uuid.uuid4(), len(cpu.get_threads()) - 1, STATIC)
        workloads = {
            w.get_id(): w
        }
        request = AllocateThreadsRequest(cpu, w.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        log.info("{}".format(cpu))
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(0, len(violations))

        # Assign another workload which will force core sharing
        w = get_test_workload(uuid.uuid4(), 1, STATIC)
        workloads[w.get_id()] = w
        request = AllocateThreadsRequest(cpu, w.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        log.info("{}".format(cpu))
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(1, len(violations))

    def test_external_cpu_manipulation(self):
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
        allocator = GreedyCpuAllocator()
        w = get_test_workload(uuid.uuid4(), 2, STATIC)
        workloads = {
            w.get_id(): w
        }
        request = AllocateThreadsRequest(cpu, w.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu = allocator.assign_threads(request).get_cpu()
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(2, len(violations))
