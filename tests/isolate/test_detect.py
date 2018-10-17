import unittest
import uuid

from tests.utils import get_test_cpu
from titus_isolate.isolate.cpu import assign_threads
from titus_isolate.isolate.detect import get_cross_package_violations
from titus_isolate.model.workload import Workload


class TestDetect(unittest.TestCase):

    def test_no_cross_package_violation(self):
        cpu = get_test_cpu()
        w = Workload(uuid.uuid4(), 4)

        assign_threads(cpu, w)
        self.assertEqual(0, len(get_cross_package_violations(cpu)))

    def test_one_cross_package_violation(self):
        cpu = get_test_cpu()
        w = Workload(uuid.uuid4(), 9)

        assign_threads(cpu, w)
        violations = get_cross_package_violations(cpu)
        self.assertEqual(1, len(violations))
