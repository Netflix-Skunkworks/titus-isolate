import logging
import unittest
import uuid

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.docker.mock_docker import MockDockerClient, MockContainer
from tests.utils import config_logs
from titus_isolate.docker.constants import STATIC, BURST
from titus_isolate.isolate.cpu import assign_threads
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_logger

from titus_optimize.compute import optimize_ip

config_logs(logging.DEBUG)
log = get_logger(logging.DEBUG)


class TestWorkloadManager(unittest.TestCase):

    def test_single_static_workload_lifecycle(self):
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)

        cgroup_manager = MockCgroupManager()
        workload_manager = WorkloadManager(get_cpu(), cgroup_manager)

        # Add workload
        workload_manager.add_workload(workload)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))
        self.assertEqual(1, cgroup_manager.container_update_counts[workload.get_id()])

        # Remove workload
        workload_manager.remove_workload(workload.get_id())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_single_burst_workload_lifecycle(self):
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, BURST)

        cgroup_manager = MockCgroupManager()
        workload_manager = WorkloadManager(get_cpu(), cgroup_manager)

        # Add workload
        workload_manager.add_workload(workload)
        self.assertEqual(1, cgroup_manager.container_update_counts[workload.get_id()])

        # All threads should have been assigned to the only burst workload.
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cgroup_manager.container_update_map[workload.get_id()]))

        # No threads should have been consumed from the cpu model perspective.
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove workload
        workload_manager.remove_workload(workload.get_id())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_remove_unknown_workload(self):
        unknown_workload_id = "unknown"
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)

        docker_client = MockDockerClient([MockContainer(workload)])
        workload_manager = WorkloadManager(get_cpu(), docker_client)

        # Remove from empty set
        workload_manager.remove_workload([unknown_workload_id])

        # Add workload
        workload_manager.add_workload(workload)
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Removal of an unknown workload should have no effect
        workload_manager.remove_workload([unknown_workload_id])
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove workload with unknown workload, real workload should be removed
        workload_manager.remove_workload(unknown_workload_id)
        workload_manager.remove_workload(workload.get_id())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(workload_manager.get_cpu().get_empty_threads()))

    def test_alternating_static_burst_workloads(self):
        thread_count = 2

        burst0 = Workload("burst0", thread_count, BURST)
        burst1 = Workload("burst1", thread_count, BURST)
        static0 = Workload("static0", thread_count, STATIC)
        static1 = Workload("static1", thread_count, STATIC)

        cgroup_manager = MockCgroupManager()
        workload_manager = WorkloadManager(get_cpu(), cgroup_manager)

        # Add static workload
        log.info("ADDING STATIC0")
        workload_manager.add_workload(static0)
        self.assertTrue(static0.get_id() in cgroup_manager.container_update_map)
        self.assertEqual(thread_count, len(cgroup_manager.container_update_map[static0.get_id()]))
        self.assertEqual(1, cgroup_manager.container_update_counts[static0.get_id()])
        expected_free_thread_count = DEFAULT_TOTAL_THREAD_COUNT - thread_count
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Add burst workload
        log.info("ADDING BURST0")
        workload_manager.add_workload(burst0)
        self.assertEqual(expected_free_thread_count, len(cgroup_manager.container_update_map[burst0.get_id()]))
        self.assertEqual(1, cgroup_manager.container_update_counts[burst0.get_id()])
        # No change in empty threads expected
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Add static workload
        log.info("ADDING STATIC1")
        workload_manager.add_workload(static1)
        self.assertEqual(thread_count, len(cgroup_manager.container_update_map[static1.get_id()]))
        self.assertEqual(1, cgroup_manager.container_update_counts[static1.get_id()])
        expected_free_thread_count = expected_free_thread_count - thread_count
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))
        # The burst0 container should be updated again because the burst footprint changed after the addition of a
        # static workload
        self.assertEqual(2, cgroup_manager.container_update_counts[burst0.get_id()])
        self.assertEqual(expected_free_thread_count, len(cgroup_manager.container_update_map[burst0.get_id()]))

        # Add burst workload
        log.info("ADDING BURST1")
        workload_manager.add_workload(burst1)
        self.assertEqual(3, cgroup_manager.container_update_counts[burst0.get_id()])
        self.assertEqual(1, cgroup_manager.container_update_counts[burst1.get_id()])
        self.assertEqual(expected_free_thread_count, len(cgroup_manager.container_update_map[burst1.get_id()]))
        # No change in empty threads expected
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))

        # Remove static workload
        log.info("REMOVING STATIC0")
        workload_manager.remove_workload(static0.get_id())
        self.assertEqual(4, cgroup_manager.container_update_counts[burst0.get_id()])
        self.assertEqual(2, cgroup_manager.container_update_counts[burst1.get_id()])
        # Empty threads should have increased
        expected_free_thread_count = expected_free_thread_count + thread_count
        self.assertEqual(expected_free_thread_count, len(workload_manager.get_cpu().get_empty_threads()))
        self.assertEqual(expected_free_thread_count, len(cgroup_manager.container_update_map[burst0.get_id()]))
        self.assertEqual(expected_free_thread_count, len(cgroup_manager.container_update_map[burst1.get_id()]))

    def test_no_cross_packages_placement_no_bad_affinity(self):

        w_a = Workload("a", 3, STATIC)
        w_b = Workload("b", 2, STATIC)
        w_c = Workload("c", 1, STATIC)
        w_d = Workload("d", 2, STATIC)

        cpu = get_cpu(package_count=2, cores_per_package=2, threads_per_core=2)

        workload_manager = WorkloadManager(cpu, MockCgroupManager())
        workload_manager.add_workload(w_a)
        workload_manager.add_workload(w_b)
        workload_manager.add_workload(w_c)
        workload_manager.add_workload(w_d)

        self.assertEqual(0, len(get_cross_package_violations(workload_manager.get_cpu())))
        #self.assertEqual(1, len(get_shared_core_violations(workload_manager.get_cpu())))  # todo: fix me
        self.assertEqual(0, len(workload_manager.get_cpu().get_empty_threads()))

