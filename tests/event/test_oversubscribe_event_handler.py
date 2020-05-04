import json
import unittest
import uuid
from datetime import datetime
from typing import List, Optional, Dict

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import get_test_workload
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import DEFAULT_TOTAL_THRESHOLD
from titus_isolate.event.constants import OVERSUBSCRIBE_EVENT, STATIC
from titus_isolate.crd.publish.opportunistic_window_publisher import OpportunisticWindowPublisher
from titus_isolate.event.oversubscribe_event_handler import OversubscribeEventHandler
from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.resource_usage import GlobalResourceUsage
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager
from titus_isolate.predict.simple_cpu_predictor import SimpleCpuPredictor
from titus_isolate.utils import set_config_manager, set_cpu_usage_predictor_manager, set_workload_monitor_manager


class TestWorkloadManager:
    def __init__(self, workloads: List[Workload]):
        self.workloads = workloads

    def get_workloads(self) -> List[Workload]:
        return self.workloads


class TestOpportunisticWindowPublisher(OpportunisticWindowPublisher):

    def __init__(self, is_window_active_func, add_window_func, cleanup_func):
        self.is_window_active_func = is_window_active_func
        self.add_window_func = add_window_func
        self.cleanup_func = cleanup_func

        self.is_window_active_count = 0
        self.add_window_count = 0
        self.cleanup_count = 0

    def is_window_active(self) -> bool:
        self.is_window_active_count += 1
        return self.is_window_active_func()

    def add_window(self, start: datetime, end: datetime, free_cpu_count: int):
        self.add_window_count += 1
        return self.add_window_func()

    def cleanup(self):
        self.cleanup_count += 1
        return self.cleanup_func()


class TestSimpleCpuPredictor(SimpleCpuPredictor):

    def __init__(self, predictions: Dict[str, float]):
        self.predictions = predictions

    def get_cpu_predictions(self, workloads: List[Workload], resource_usage: GlobalResourceUsage) -> Optional[
        Dict[str, float]]:
        return self.predictions


class TestCpuUsagePredictorManager(CpuUsagePredictorManager):

    def __init__(self, predictor: SimpleCpuPredictor):
        self.predictor = predictor

    def get_cpu_predictor(self) -> Optional[SimpleCpuPredictor]:
        return self.predictor


class TestWorkloadMonitorManager:

    @staticmethod
    def get_pcp_usage() -> dict:
        return {}

    def get_resource_usage(self) -> GlobalResourceUsage:
        return GlobalResourceUsage(self.get_pcp_usage())


class TestOversubscribeEventHandler(unittest.TestCase):

    def test_skip_active_window(self):
        set_config_manager(ConfigManager(TestPropertyProvider({})))
        window_publisher = TestOpportunisticWindowPublisher(
            is_window_active_func=lambda: True,
            add_window_func=lambda: None,
            cleanup_func=lambda: None
        )

        oeh = OversubscribeEventHandler(TestWorkloadManager([]), window_publisher)
        oeh._handle(json.loads(OVERSUBSCRIBE_EVENT.decode("utf-8")))

        self.assertEqual(1, oeh.get_skip_count())
        self.assertEqual(1, window_publisher.is_window_active_count)

    def test_publish_window(self):
        set_config_manager(ConfigManager(TestPropertyProvider({})))
        set_workload_monitor_manager(TestWorkloadMonitorManager())
        window_publisher = TestOpportunisticWindowPublisher(
            is_window_active_func=lambda: False,
            add_window_func=lambda: None,
            cleanup_func=lambda: None
        )

        w_id = str(uuid.uuid4())
        workload = get_test_workload(w_id, 1, STATIC)

        set_cpu_usage_predictor_manager(
            TestCpuUsagePredictorManager(
                TestSimpleCpuPredictor({
                    w_id: DEFAULT_TOTAL_THRESHOLD - 0.001
                })))

        oeh = OversubscribeEventHandler(TestWorkloadManager([workload]), window_publisher)
        oeh._handle(json.loads(OVERSUBSCRIBE_EVENT.decode("utf-8")))

        self.assertEqual(0, oeh.get_skip_count())
        self.assertEqual(1, oeh.get_success_count())
        self.assertEqual(1, window_publisher.is_window_active_count)
        self.assertEqual(1, window_publisher.add_window_count)
