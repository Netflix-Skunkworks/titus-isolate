import json
import unittest
import uuid

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.docker.mock_docker import MockDockerClient, MockContainer
from tests.utils import wait_until
from titus_isolate.api import status
from titus_isolate.api.status import set_wm, get_workloads, get_violations, get_wm_status
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_PACKAGE_COUNT, DEFAULT_CORE_COUNT, DEFAULT_THREAD_COUNT
from titus_isolate.model.workload import Workload


class TestStatus(unittest.TestCase):

    def test_get_workloads_endpoint(self):
        cpu = get_cpu()
        thread_count = 2
        workload_id = str(uuid.uuid4())
        workload = Workload(workload_id, thread_count, STATIC)

        docker_client = MockDockerClient([MockContainer(workload)])
        workload_manager = WorkloadManager(cpu, docker_client)
        set_wm(workload_manager)

        workloads = json.loads(get_workloads())
        self.assertEqual(0, len(workloads))

        workload_manager.add_workloads([workload])
        wait_until(lambda: len(json.loads(get_workloads())) == 1)
        workloads = json.loads(get_workloads())
        self.assertEqual(workload_id, workloads[0]["id"])
        self.assertEqual(STATIC, workloads[0]["type"])
        self.assertEqual(thread_count, workloads[0]["thread_count"])

    def test_get_cpu_endpoint(self):
        set_wm(self.__get_default_workload_manager())

        cpu_dict = json.loads(status.get_cpu())
        self.assertEqual(1, len(cpu_dict))
        self.assertEqual(DEFAULT_PACKAGE_COUNT, len(cpu_dict["packages"]))
        for p in cpu_dict["packages"]:
            self.assertEqual(DEFAULT_CORE_COUNT, len(p["cores"]))
            for c in p["cores"]:
                self.assertEqual(DEFAULT_THREAD_COUNT, len(c["threads"]))

    def test_get_violations_endpoint(self):
        set_wm(self.__get_default_workload_manager())

        violations = json.loads(get_violations())
        self.assertEqual(2, len(violations))

    def test_get_wm_status_endpoint(self):
        set_wm(self.__get_default_workload_manager())

        s = json.loads(get_wm_status())
        self.assertEqual(3, len(s))

    @staticmethod
    def __get_default_workload_manager():
        cpu = get_cpu()
        thread_count = 2
        workload_id = str(uuid.uuid4())

        return WorkloadManager(cpu, MockCgroupManager())
