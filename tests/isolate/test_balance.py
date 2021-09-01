import unittest
import uuid

from tests.utils import get_test_workload, get_allocate_request
from titus_isolate.isolate.balance import has_better_isolation
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.model.processor.config import get_cpu


class TestBalance(unittest.TestCase):

    def test_no_change_empty_cpu(self):
        cpu = get_cpu()
        self.assertFalse(has_better_isolation(cpu, cpu))

    def test_no_change_populated_cpu(self):
        w0 = get_test_workload(uuid.uuid4(), 4)

        cur_cpu = get_cpu()
        new_cpu = get_cpu()

        allocator0 = GreedyCpuAllocator()
        request = get_allocate_request(cur_cpu, [w0])
        cur_cpu = allocator0.isolate(request).get_cpu()

        allocator1 = GreedyCpuAllocator()
        request = get_allocate_request(new_cpu, [w0])
        new_cpu = allocator1.isolate(request).get_cpu()

        self.assertFalse(has_better_isolation(cur_cpu, new_cpu))

    def test_cross_package_violations_have_decreased(self):
        workload_id_0 = "w0"
        workload_id_1 = "w1"

        # Put 2 cross package violation on the current cpu
        cur_cpu = get_cpu()

        # W0 is on the first threads of package 0 and 1
        cur_cpu.get_packages()[0].get_threads()[0].claim(workload_id_0)
        cur_cpu.get_packages()[1].get_threads()[0].claim(workload_id_0)

        # W1 is on the second threads of package 0 and 1
        cur_cpu.get_packages()[0].get_threads()[1].claim(workload_id_1)
        cur_cpu.get_packages()[1].get_threads()[1].claim(workload_id_1)

        # Put 1 cross package violation on the new cpu
        new_cpu = get_cpu()

        # W0 is on the first threads of package 0 and 1 (unchanged)
        new_cpu.get_packages()[0].get_threads()[0].claim(workload_id_0)
        new_cpu.get_packages()[1].get_threads()[0].claim(workload_id_0)

        # W1 is on the second and third threads of package 0 (better)
        new_cpu.get_packages()[0].get_threads()[1].claim(workload_id_1)
        new_cpu.get_packages()[0].get_threads()[2].claim(workload_id_1)

        self.assertTrue(has_better_isolation(cur_cpu, new_cpu))

    def test_cross_package_violations_have_increased(self):
        workload_id_0 = "w0"
        workload_id_1 = "w1"

        # Put 1 cross package violation on the new cpu
        cur_cpu = get_cpu()

        # W0 is on the first threads of package 0 and 1 (unchanged)
        cur_cpu.get_packages()[0].get_threads()[0].claim(workload_id_0)
        cur_cpu.get_packages()[1].get_threads()[0].claim(workload_id_0)

        # Put 2 cross package violation on the current cpu
        new_cpu = get_cpu()

        # W0 is on the first threads of package 0 and 1
        new_cpu.get_packages()[0].get_threads()[0].claim(workload_id_0)
        new_cpu.get_packages()[1].get_threads()[0].claim(workload_id_0)

        # W1 is on the second threads of package 0 and 1
        new_cpu.get_packages()[0].get_threads()[1].claim(workload_id_1)
        new_cpu.get_packages()[1].get_threads()[1].claim(workload_id_1)

        self.assertFalse(has_better_isolation(cur_cpu, new_cpu))

    def test_only_shared_cores_have_decreased(self):
        workload_id_0 = "w0"
        workload_id_1 = "w1"

        # Share two cores on the current cpu
        cur_cpu = get_cpu()

        # Core 0 is shared by w0 and w1
        cur_cpu.get_packages()[0].get_cores()[0].get_threads()[0].claim(workload_id_0)
        cur_cpu.get_packages()[0].get_cores()[0].get_threads()[1].claim(workload_id_1)

        # Core 1 is shared by w0 and w1
        cur_cpu.get_packages()[0].get_cores()[1].get_threads()[0].claim(workload_id_0)
        cur_cpu.get_packages()[0].get_cores()[1].get_threads()[1].claim(workload_id_1)

        # Share zero cores on the new cpu
        new_cpu = get_cpu()

        # Core 0 is wholly consumed by w0
        new_cpu.get_packages()[0].get_cores()[0].get_threads()[0].claim(workload_id_0)
        new_cpu.get_packages()[0].get_cores()[0].get_threads()[1].claim(workload_id_0)

        # Core 1 is wholly consumed by w1
        new_cpu.get_packages()[0].get_cores()[1].get_threads()[0].claim(workload_id_1)
        new_cpu.get_packages()[0].get_cores()[1].get_threads()[1].claim(workload_id_1)

        self.assertTrue(has_better_isolation(cur_cpu, new_cpu))

    def test_only_shared_cores_have_increased(self):
        workload_id_0 = "w0"
        workload_id_1 = "w1"

        # Share two cores on the current cpu
        cur_cpu = get_cpu()

        # Core 0 is wholly consumed by w0
        cur_cpu.get_packages()[0].get_cores()[0].get_threads()[0].claim(workload_id_0)
        cur_cpu.get_packages()[0].get_cores()[0].get_threads()[1].claim(workload_id_0)

        # Core 1 is wholly consumed by w1
        cur_cpu.get_packages()[0].get_cores()[1].get_threads()[0].claim(workload_id_1)
        cur_cpu.get_packages()[0].get_cores()[1].get_threads()[1].claim(workload_id_1)

        # Share zero cores on the new cpu
        new_cpu = get_cpu()

        # Core 0 is shared by w0 and w1
        new_cpu.get_packages()[0].get_cores()[0].get_threads()[0].claim(workload_id_0)
        new_cpu.get_packages()[0].get_cores()[0].get_threads()[1].claim(workload_id_1)

        # Core 1 is shared by w0 and w1
        new_cpu.get_packages()[0].get_cores()[1].get_threads()[0].claim(workload_id_0)
        new_cpu.get_packages()[0].get_cores()[1].get_threads()[1].claim(workload_id_1)

        self.assertFalse(has_better_isolation(cur_cpu, new_cpu))
