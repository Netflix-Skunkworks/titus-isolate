import logging
import unittest
import uuid

from spectator import Registry

from tests.docker.mock_docker import MockEventProvider, get_container_create_event
from tests.docker.test_events import DEFAULT_CPU_COUNT
from tests.utils import wait_until, config_logs, TestContext
from titus_isolate.docker.constants import STATIC
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.metrics.metrics_reporter import ADDED_KEY, SUCCEEDED_KEY, FAILED_KEY, PACKAGE_VIOLATIONS_KEY, \
    CORE_VIOLATIONS_KEY, QUEUE_DEPTH_KEY, override_registry, MetricsReporter, REMOVED_KEY, REBALANCED_KEY, \
    REBALANCED_NOOP_KEY, WORKLOAD_COUNT_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY
from titus_isolate.utils import get_logger

config_logs(logging.DEBUG)
log = get_logger(logging.DEBUG)


class TestMetricsReporter(unittest.TestCase):

    @staticmethod
    def __gauge_value_reached(registry, key, expected_value):
        value = registry.gauge(key).get()
        log.debug("gauge: '{}'='{}' expected: '{}'".format(key, value, expected_value))
        return value == expected_value

    def test_empty_metrics(self):
        registry = Registry()
        override_registry(registry)

        test_context = TestContext()
        event_manager = EventManager(MockEventProvider([]), [], 0.01)

        MetricsReporter(test_context.get_workload_manager(), event_manager, registry, 0.01, 0.01)

        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_NOOP_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, WORKLOAD_COUNT_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_SUCCEEDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_PROCESSED_KEY, 0))

        event_manager.stop_processing_events()

    def test_add_metrics(self):
        registry = Registry()
        override_registry(registry)

        test_context = TestContext()
        workload_name = str(uuid.uuid4())
        events = [get_container_create_event(DEFAULT_CPU_COUNT, STATIC, workload_name, workload_name)]
        event_manager = EventManager(MockEventProvider(events), test_context.get_event_handlers(), 0.01)

        workload_manager = test_context.get_workload_manager()
        MetricsReporter(workload_manager, event_manager, registry, 0.01, 0.01)

        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_NOOP_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 2))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, WORKLOAD_COUNT_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_SUCCEEDED_KEY, 3))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_PROCESSED_KEY, 1))

        event_manager.stop_processing_events()
