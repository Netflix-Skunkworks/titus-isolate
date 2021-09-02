import logging
import unittest
import uuid

from spectator import Registry

from tests.allocate.test_allocate import TestWorkloadMonitorManager, TestPodManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.event.mock_docker import get_container_create_event, MockEventProvider, get_event, get_container_die_event
from tests.utils import config_logs, wait_until, TestContext, gauge_value_equals, counter_value_equals, \
    get_simple_test_pod
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.event.constants import CONTAINER, REBALANCE_EVENT, START
from titus_isolate.event.event_manager import EventManager
from titus_isolate.metrics.constants import QUEUE_DEPTH_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.utils import set_config_manager, set_workload_monitor_manager, set_pod_manager, get_pod_manager

# This import is necessary for the tests below to work
from tests.event.mock_titus_environment import MOCK_TITUS_ENVIRONMENT

DEFAULT_CPU_COUNT = 2

config_logs(logging.DEBUG)

DEFAULT_TEST_EVENT_TIMEOUT_SECS = 0.01
set_config_manager(ConfigManager(TestPropertyProvider({})))
set_workload_monitor_manager(TestWorkloadMonitorManager())
set_pod_manager(TestPodManager())


class TestEvents(unittest.TestCase):

    def test_update_mock_container(self):
        registry = Registry()
        test_pod = get_simple_test_pod()
        get_pod_manager().set_pod(test_pod)
        workload_name = test_pod.metadata.name

        events = [get_container_create_event(DEFAULT_CPU_COUNT, workload_name, workload_name)]
        event_count = len(events)
        event_iterable = MockEventProvider(events)

        test_context = TestContext()
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry, {})
        manager.start_processing_events()

        wait_until(lambda: event_count == manager.get_processed_count())
        self.assertEqual(0, manager.get_queue_depth())
        self.assertEqual(event_count, test_context.get_workload_manager().get_success_count())
        self.assertEqual(
            DEFAULT_TOTAL_THREAD_COUNT - DEFAULT_CPU_COUNT,
            len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(1, test_context.get_container_batch_event_handler().get_handled_event_count())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_SUCCEEDED_KEY, event_count * len(test_context.get_event_handlers())))
        self.assertTrue(counter_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_PROCESSED_KEY, event_count))

    def test_free_cpu_on_container_die(self):
        registry = Registry()
        test_pod = get_simple_test_pod()
        get_pod_manager().set_pod(test_pod)
        workload_name = test_pod.metadata.name

        events = [
            get_container_create_event(DEFAULT_CPU_COUNT, workload_name, workload_name),
            get_container_die_event(workload_name)]
        event_count = len(events)
        event_iterable = MockEventProvider(events, 1)  # Force in order event processing for the test

        test_context = TestContext()
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry, {})
        manager.start_processing_events()

        wait_until(lambda: event_count == manager.get_processed_count())
        self.assertEqual(0, manager.get_queue_depth())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(2, test_context.get_container_batch_event_handler().get_handled_event_count())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_SUCCEEDED_KEY, event_count * len(test_context.get_event_handlers())))
        self.assertTrue(counter_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_PROCESSED_KEY, event_count))

    def test_absent_name_label(self):
        registry = Registry()
        test_context = TestContext()
        name = str(uuid.uuid4())
        unknown_event = get_event(
            CONTAINER,
            START,
            name,
            {})
        event_handlers = test_context.get_event_handlers()
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, event_handlers, DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry, {})
        manager.start_processing_events()

        wait_until(lambda: test_context.get_container_batch_event_handler().get_ignored_event_count() == 1)
        self.assertEqual(0, manager.get_queue_depth())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_SUCCEEDED_KEY, len(test_context.get_event_handlers())))
        self.assertTrue(counter_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_PROCESSED_KEY, 1))

    def test_rebalance(self):
        registry = Registry()

        events = [REBALANCE_EVENT]
        event_count = len(events)
        event_iterable = MockEventProvider(events)

        test_context = TestContext()
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry, {})
        manager.start_processing_events()

        wait_until(lambda: event_count == manager.get_processed_count())
        self.assertEqual(0, manager.get_queue_depth())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(0, test_context.get_container_batch_event_handler().get_handled_event_count())
        self.assertEqual(1, test_context.get_rebalance_event_handler().get_handled_event_count())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_SUCCEEDED_KEY, event_count * len(test_context.get_event_handlers())))
        self.assertTrue(counter_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(counter_value_equals(registry, EVENT_PROCESSED_KEY, event_count))
