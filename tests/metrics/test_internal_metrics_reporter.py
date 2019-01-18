import logging
import unittest
import uuid

from spectator import Registry

from tests.docker.mock_docker import MockEventProvider, get_container_create_event, get_container_die_event
from tests.docker.test_events import DEFAULT_CPU_COUNT
from tests.utils import wait_until, config_logs, TestContext, get_fake_cpu, get_mock_file_manager
from titus_isolate import log
from titus_isolate.docker.constants import STATIC
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.metrics.internal_metrics_reporter import ADDED_KEY, SUCCEEDED_KEY, FAILED_KEY, \
    PACKAGE_VIOLATIONS_KEY, \
    CORE_VIOLATIONS_KEY, QUEUE_DEPTH_KEY, InternalMetricsReporter, REMOVED_KEY, \
    WORKLOAD_COUNT_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY, RUNNING, \
    FALLBACK_ALLOCATOR_COUNT, IP_ALLOCATOR_TIMEBOUND_COUNT, ALLOCATOR_CALL_DURATION

config_logs(logging.DEBUG)


class TestInternalMetricsReporter(unittest.TestCase):

    @staticmethod
    def __gauge_value_equals(registry, key, expected_value):
        value = registry.gauge(key).get()
        log.debug("gauge: '{}'='{}' expected: '{}'".format(key, value, expected_value))
        return value == expected_value

    @staticmethod
    def __gauge_value_reached(registry, key, min_expected_value):
        value = registry.gauge(key).get()
        log.debug("gauge: '{}'='{}' min expected: '{}'".format(key, value, min_expected_value))
        return value >= min_expected_value

    def test_empty_metrics(self):

        test_context = TestContext()
        event_manager = EventManager(MockEventProvider([]), [], get_mock_file_manager(), 0.01)

        registry = Registry()
        reporter = InternalMetricsReporter(test_context.get_workload_manager(), event_manager)
        reporter.set_registry(registry)
        reporter.report_metrics({})

        wait_until(lambda: self.__gauge_value_equals(registry, RUNNING, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, ADDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, SUCCEEDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, CORE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_PROCESSED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, FALLBACK_ALLOCATOR_COUNT, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, IP_ALLOCATOR_TIMEBOUND_COUNT, 0))

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

        wait_until(lambda: self.__gauge_value_equals(registry, RUNNING, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, ADDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, SUCCEEDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, CORE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, 3))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_PROCESSED_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, FALLBACK_ALLOCATOR_COUNT, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, IP_ALLOCATOR_TIMEBOUND_COUNT, 0))

        event_manager.stop_processing_events()

    def test_edge_case_ip_allocator_metrics(self):
        # this is a specific scenario causing troubles to the solver.
        # we should hit the time-bound limit and report it.

        cpu = get_fake_cpu(2,64)
        test_context = TestContext(cpu=cpu)
        test_context.get_workload_manager().get_allocator().set_solver_max_runtime_secs(0.01)
        events = []
        cnt_evts = 0

        for i in range(15):
            events.append(get_container_create_event(2, name=str(i), id=str(i)))
        cnt_evts += 15

        events.append(get_container_create_event(1, name="15", id="15"))
        cnt_evts += 1

        for i in range(9):
            events.append(get_container_create_event(2, name=str(i+cnt_evts), id=str(i+cnt_evts)))

        events.append(get_container_die_event(name="15", id="15"))

        event_count = len(events)
        event_manager = EventManager(
            MockEventProvider(events),
            test_context.get_event_handlers(),
            get_mock_file_manager(),
            5.0)
        
        wait_until(lambda: event_count == event_manager.get_processed_count(), timeout=20)

        log.info("Event manager has processed {} events.".format(event_manager.get_processed_count()))

        workload_manager = test_context.get_workload_manager()
        registry = Registry()
        reporter = InternalMetricsReporter(workload_manager, event_manager)
        reporter.set_registry(registry)
        reporter.report_metrics({})

        wait_until(lambda: self.__gauge_value_equals(registry, RUNNING, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, ADDED_KEY, 25))
        wait_until(lambda: self.__gauge_value_equals(registry, REMOVED_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, SUCCEEDED_KEY, 26))
        wait_until(lambda: self.__gauge_value_equals(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 24))
        wait_until(lambda: self.__gauge_value_equals(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, 3 * 26))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, EVENT_PROCESSED_KEY, 26))
        wait_until(lambda: self.__gauge_value_reached(registry, IP_ALLOCATOR_TIMEBOUND_COUNT, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, ALLOCATOR_CALL_DURATION, 0.1))

        event_manager.stop_processing_events()

    def test_crash_ip_allocator_metrics(self):

        cpu = get_fake_cpu(2,64)
        test_context = TestContext(cpu=cpu)

        # now override the cpu seen by the allocator to crash it
        test_context.get_workload_manager().get_allocator().set_cpu(get_fake_cpu(2, 8))

        events = [get_container_create_event(10, name="foo", id="bar")]
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

        wait_until(lambda: self.__gauge_value_equals(registry, RUNNING, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, ADDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, SUCCEEDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_equals(registry, WORKLOAD_COUNT_KEY, 1))
        wait_until(lambda: self.__gauge_value_equals(registry, FALLBACK_ALLOCATOR_COUNT, 1))

        event_manager.stop_processing_events()