import unittest
from typing import List

from tests.config.test_property_provider import TestPropertyProvider
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.event.constants import OVERSUBSCRIBE_EVENT
from titus_isolate.event.oversubscribe_event_handler import OversubscribeEventHandler
from titus_isolate.model.workload_interface import Workload
from titus_isolate.utils import set_config_manager


class TestWorkloadManager:
    def __init__(self, workloads: List[Workload]):
        self.workloads = workloads

    def get_workloads(self) ->  List[Workload]:
        return self.workloads


class TestOversubscribeEventHandler(unittest.TestCase):

    def test_no_workloads(self):
        set_config_manager(ConfigManager(TestPropertyProvider({})))

        oeh = OversubscribeEventHandler(TestWorkloadManager([]))
        oeh.handle(OVERSUBSCRIBE_EVENT)

