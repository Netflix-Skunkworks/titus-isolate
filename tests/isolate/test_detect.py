import logging
import unittest
import uuid

from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.cpu import assign_threads
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_logger

log = get_logger(logging.DEBUG)


class TestDetect(unittest.TestCase):

    def test_no_cross_package_violation(self):
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), 4, STATIC)

        violations = get_cross_package_violations(cpu)
        log.info("cross package violations: {}".format(violations))
        self.assertEqual(0, len(violations))

        assign_threads(cpu, w)
        violations = get_cross_package_violations(cpu)
        log.info("cross package violations: {}".format(violations))
        self.assertEqual(0, len(violations))

    def test_one_cross_package_violation(self):
        cpu = get_cpu()
        w = Workload(uuid.uuid4(), 9, STATIC)

        assign_threads(cpu, w)
        violations = get_cross_package_violations(cpu)
        log.info("cross package violations: {}".format(violations))
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
        w = Workload(uuid.uuid4(), 2, STATIC)
        assign_threads(cpu, w, {dummy_workload_id: 0})
        violations = get_shared_core_violations(cpu)
        log.info("shared core violations: {}".format(violations))
        self.assertEqual(2, len(violations))
