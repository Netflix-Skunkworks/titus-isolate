import json
import unittest
import uuid

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.docker.mock_docker import MockEventProvider
from titus_isolate.api import status
from titus_isolate.api.status import set_wm, get_workloads, get_violations, get_wm_status, set_em
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.docker.constants import STATIC
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_PACKAGE_COUNT, DEFAULT_CORE_COUNT, DEFAULT_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import override_config_manager


class TestStatus(unittest.TestCase):

    def test_get_workloads_endpoint(self):
        override_config_manager(ConfigManager(TestPropertyProvider({})))

        cpu = get_cpu()
        thread_count = 2
        workload_id = str(uuid.uuid4())
        workload = Workload(workload_id, thread_count, STATIC)

        workload_manager = WorkloadManager(cpu, MockCgroupManager())
        set_wm(workload_manager)

        workloads = json.loads(get_workloads())
        self.assertEqual(0, len(workloads))

        workload_manager.add_workload(workload)
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

        event_manager = EventManager(MockEventProvider([]), [], 0.01)
        set_em(event_manager)
        event_manager.start_processing_events()

        s = json.loads(get_wm_status())
        self.assertEqual(2, len(s))
        self.assertEqual(4, len(s["event_manager"]))
        self.assertEqual(6, len(s["workload_manager"]))

        event_manager.stop_processing_events()

    @staticmethod
    def __get_default_workload_manager():
        cpu = get_cpu()
        return WorkloadManager(cpu, MockCgroupManager())
