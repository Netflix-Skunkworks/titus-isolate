import unittest
import uuid

from spectator import Registry

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.docker.mock_docker import MockDockerClient
from tests.utils import get_test_container, gauge_value_equals
from titus_isolate.docker.constants import STATIC
from titus_isolate.gc.workload_gc import WorkloadGarbageCollector
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import WORKLOAD_GC_COUNT_KEY
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload


class TestWorkloadManager(unittest.TestCase):

    def test_empty_workloads(self):
        docker_client = MockDockerClient()
        workload_manager = WorkloadManager(get_cpu(), MockCgroupManager())

        gc = WorkloadGarbageCollector(workload_manager, docker_client)
        self.assertEqual(0, workload_manager.get_added_count())
        self.assertEqual(0, workload_manager.get_removed_count())

        gc._gc_workloads()
        self.assertEqual(0, workload_manager.get_added_count())
        self.assertEqual(0, workload_manager.get_removed_count())

        self.__assert_gc_count(gc, 0)

    def test_extra_docker_container_does_nothing(self):
        docker_client = MockDockerClient()
        docker_client.add_container(get_test_container(uuid.uuid4(), 2))
        workload_manager = WorkloadManager(get_cpu(), MockCgroupManager())

        gc = WorkloadGarbageCollector(workload_manager, docker_client)
        self.assertEqual(0, workload_manager.get_added_count())
        self.assertEqual(0, workload_manager.get_removed_count())

        gc._gc_workloads()
        self.assertEqual(0, workload_manager.get_added_count())
        self.assertEqual(0, workload_manager.get_removed_count())

        self.__assert_gc_count(gc, 0)

    def test_extra_wm_container_is_removed(self):
        docker_client = MockDockerClient()
        workload_manager = WorkloadManager(get_cpu(), MockCgroupManager())

        gc = WorkloadGarbageCollector(workload_manager, docker_client)
        self.assertEqual(0, workload_manager.get_added_count())
        self.assertEqual(0, workload_manager.get_removed_count())

        workload_manager.add_workload(Workload(uuid.uuid4(), 2, STATIC))
        self.assertEqual(1, workload_manager.get_added_count())
        self.assertEqual(0, workload_manager.get_removed_count())

        gc._gc_workloads()
        self.assertEqual(1, workload_manager.get_added_count())
        self.assertEqual(1, workload_manager.get_removed_count())

        self.__assert_gc_count(gc, 1)

    def __assert_gc_count(self, gc, count):
        registry = Registry()
        gc.set_registry(registry)
        gc.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, WORKLOAD_GC_COUNT_KEY, count))
