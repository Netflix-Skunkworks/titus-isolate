import json
import logging
import unittest
import uuid


from tests.allocate.test_allocate import TestWorkloadMonitorManager
from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.event.mock_docker import MockEventProvider
from tests.utils import get_test_workload, config_logs, DEFAULT_TEST_JOB_ID
from titus_isolate.allocate.naive_cpu_allocator import NaiveCpuAllocator
from titus_isolate.api import status
from titus_isolate.api.status import get_workloads, get_violations, get_wm_status, get_isolated_workload_ids, \
    isolate_workload
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.event.event_manager import EventManager
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.constants import TASK_ID_KEY, JOB_ID_KEY, THREAD_COUNT_KEY
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_PACKAGE_COUNT, DEFAULT_CORE_COUNT, DEFAULT_THREAD_COUNT
from titus_isolate.utils import set_config_manager, set_workload_manager, set_event_manager, \
    set_workload_monitor_manager

config_logs(logging.DEBUG)
set_workload_monitor_manager(TestWorkloadMonitorManager())


class TestStatus(unittest.TestCase):

    def test_get_workloads_endpoint(self):
        set_config_manager(ConfigManager(TestPropertyProvider({})))

        thread_count = 2
        workload_id = str(uuid.uuid4())
        workload = get_test_workload(workload_id, thread_count)

        workload_manager = self.__get_default_workload_manager()
        set_workload_manager(workload_manager)

        workloads = json.loads(get_workloads())
        self.assertEqual(0, len(workloads))

        workload_manager.isolate(adds=[workload], removes=[])

        workloads = json.loads(get_workloads())
        self.assertEqual(workload_id, workloads[0][TASK_ID_KEY])
        self.assertEqual(DEFAULT_TEST_JOB_ID, workloads[0][JOB_ID_KEY])
        self.assertEqual(thread_count, workloads[0][THREAD_COUNT_KEY])

    def test_get_isolated_workloads_endpoint(self):
        workload_manager = self.__get_default_workload_manager()
        set_workload_manager(workload_manager)

        isolated_workload_ids = json.loads(get_isolated_workload_ids())
        self.assertEqual(0, len(isolated_workload_ids))

        workload = get_test_workload(str(uuid.uuid4()), 2)
        workload_manager.isolate(adds=[workload], removes=[])

        isolated_workload_ids = json.loads(get_isolated_workload_ids())
        self.assertEqual(1, len(isolated_workload_ids))
        self.assertEqual(workload.get_task_id(), isolated_workload_ids[0])

    def test_isolate_workload_endpoint(self):
        workload_manager = self.__get_default_workload_manager()
        set_workload_manager(workload_manager)

        _, code, _ = isolate_workload(str(uuid.uuid4()))
        self.assertEqual(404, code)

        workload = get_test_workload(str(uuid.uuid4()), 2)
        workload_manager.isolate(adds=[workload], removes=[])

        _, code, _ = isolate_workload(workload.get_task_id())
        self.assertEqual(200, code)

    def test_get_cpu_endpoint(self):
        set_workload_manager(self.__get_default_workload_manager())

        cpu_dict = json.loads(status.get_cpu())
        self.assertEqual(1, len(cpu_dict))
        self.assertEqual(DEFAULT_PACKAGE_COUNT, len(cpu_dict["packages"]))
        for p in cpu_dict["packages"]:
            self.assertEqual(DEFAULT_CORE_COUNT, len(p["cores"]))
            for c in p["cores"]:
                self.assertEqual(DEFAULT_THREAD_COUNT, len(c["threads"]))

    def test_get_violations_endpoint(self):
        set_workload_manager(self.__get_default_workload_manager())

        violations = json.loads(get_violations())
        self.assertEqual(2, len(violations))

    def test_get_wm_status_endpoint(self):
        set_workload_manager(self.__get_default_workload_manager())

        event_manager = EventManager(MockEventProvider([]), [], 0.01)
        set_event_manager(event_manager)
        event_manager.start_processing_events()

        s = json.loads(get_wm_status())
        self.assertEqual(1, len(s))
        self.assertEqual(3, len(s["workload_manager"]))

        event_manager.stop_processing_events()

    @staticmethod
    def __get_default_workload_manager():
        cpu = get_cpu()
        return WorkloadManager(cpu, MockCgroupManager(), NaiveCpuAllocator())
