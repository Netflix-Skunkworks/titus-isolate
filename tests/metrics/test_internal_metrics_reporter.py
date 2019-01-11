import logging
import unittest
import uuid

from spectator import Registry

from tests.docker.mock_docker import MockEventProvider, get_container_create_event
from tests.docker.test_events import DEFAULT_CPU_COUNT
from tests.utils import wait_until, config_logs, TestContext, get_mock_file_manager
from titus_isolate import log
from titus_isolate.docker.constants import STATIC
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.metrics.internal_metrics_reporter import ADDED_KEY, SUCCEEDED_KEY, FAILED_KEY, PACKAGE_VIOLATIONS_KEY, \
    CORE_VIOLATIONS_KEY, QUEUE_DEPTH_KEY, InternalMetricsReporter, REMOVED_KEY, \
    WORKLOAD_COUNT_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY

config_logs(logging.DEBUG)


class TestInternalMetricsReporter(unittest.TestCase):

    @staticmethod
    def __gauge_value_reached(registry, key, expected_value):
        value = registry.gauge(key).get()
        log.debug("gauge: '{}'='{}' expected: '{}'".format(key, value, expected_value))
        return value == expected_value

    def test_empty_metrics(self):

        test_context = TestContext()
        event_manager = EventManager(MockEventProvider([]), [], get_mock_file_manager(), 0.01)

        registry = Registry()
        reporter = InternalMetricsReporter(test_context.get_workload_manager(), event_manager)
        reporter.set_registry(registry)
        reporter.report_metrics({})

        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 0))
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

        test_context = TestContext()
        workload_name = str(uuid.uuid4())
        events = [get_container_create_event(DEFAULT_CPU_COUNT, STATIC, workload_name, workload_name)]
        event_count = len(events)
        event_manager = EventManager(
            MockEventProvider(events),
            test_context.get_event_handlers(),
            get_mock_file_manager(),
            5.0)
        wait_until(lambda: event_count == event_manager.get_processed_count())

        log.info("Event manager has processed {} events.".format(event_manager.get_processed_count()))

        workload_manager = test_context.get_workload_manager()
        registry = Registry()
        reporter = InternalMetricsReporter(workload_manager, event_manager)
        reporter.set_registry(registry)
        reporter.report_metrics({})

        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, WORKLOAD_COUNT_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_SUCCEEDED_KEY, 3))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, EVENT_PROCESSED_KEY, 1))

        event_manager.stop_processing_events()
