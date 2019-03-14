import logging
import unittest
import uuid

from spectator import Registry

from tests.config.test_property_provider import TestPropertyProvider
from tests.event.mock_docker import get_container_create_event, MockEventProvider, get_event, get_container_die_event
from tests.utils import config_logs, wait_until, TestContext, gauge_value_equals, DEFAULT_TEST_MEM, DEFAULT_TEST_DISK, \
    DEFAULT_TEST_NETWORK, DEFAULT_TEST_IMAGE, DEFAULT_TEST_APP_NAME, DEFAULT_TEST_JOB_TYPE, DEFAULT_TEST_OWNER_EMAIL
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.event.constants import CONTAINER, CREATE, STATIC, CPU_LABEL_KEY, WORKLOAD_TYPE_LABEL_KEY, NAME, \
    REBALANCE_EVENT, MEM_LABEL_KEY, DISK_LABEL_KEY, NETWORK_LABEL_KEY, IMAGE_LABEL_KEY, \
    APP_NAME_LABEL_KEY, JOB_TYPE_LABEL_KEY, OWNER_EMAIL_LABEL_KEY
from titus_isolate.event.event_manager import EventManager
from titus_isolate.metrics.constants import QUEUE_DEPTH_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.utils import set_config_manager

DEFAULT_CPU_COUNT = 2

config_logs(logging.DEBUG)

DEFAULT_TEST_EVENT_TIMEOUT_SECS = 0.01
set_config_manager(ConfigManager(TestPropertyProvider({})))


class TestEvents(unittest.TestCase):

    def test_update_mock_container(self):
        registry = Registry()
        workload_name = str(uuid.uuid4())

        events = [get_container_create_event(DEFAULT_CPU_COUNT, STATIC, workload_name, workload_name)]
        event_count = len(events)
        event_iterable = MockEventProvider(events)

        test_context = TestContext()
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: event_count == manager.get_processed_count())
        self.assertEqual(0, manager.get_queue_depth())
        self.assertEqual(event_count, test_context.get_workload_manager().get_success_count())
        self.assertEqual(
            DEFAULT_TOTAL_THREAD_COUNT - DEFAULT_CPU_COUNT,
            len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(1, test_context.get_create_event_handler().get_handled_event_count())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, event_count * len(test_context.get_event_handlers())))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, event_count))

    def test_free_cpu_on_container_die(self):
        registry = Registry()
        workload_name = str(uuid.uuid4())

        events = [
            get_container_create_event(DEFAULT_CPU_COUNT, STATIC, workload_name, workload_name),
            get_container_die_event(workload_name)]
        event_count = len(events)
        event_iterable = MockEventProvider(events, 1)  # Force in order event processing for the test

        test_context = TestContext()
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: event_count == manager.get_processed_count())
        self.assertEqual(0, manager.get_queue_depth())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(1, test_context.get_create_event_handler().get_handled_event_count())
        self.assertEqual(1, test_context.get_free_event_handler().get_handled_event_count())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, event_count * len(test_context.get_event_handlers())))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, event_count))

    def test_unknown_action(self):
        registry = Registry()
        test_context = TestContext()
        unknown_event = get_event(CONTAINER, "unknown", uuid.uuid4(), {})
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: test_context.get_create_event_handler().get_ignored_event_count() == 1)
        self.assertEqual(0, manager.get_queue_depth())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, len(test_context.get_event_handlers())))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, 1))

    def test_absent_cpu_label(self):
        registry = Registry()
        test_context = TestContext()
        unknown_event = get_event(
            CONTAINER,
            CREATE,
            "unknown",
            {
                WORKLOAD_TYPE_LABEL_KEY: STATIC,
                NAME: str(uuid.uuid4())
            })
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: test_context.get_create_event_handler().get_ignored_event_count() == 1)
        self.assertEqual(0, manager.get_queue_depth())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, len(test_context.get_event_handlers())))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, 1))

    def test_absent_workload_type_label(self):
        registry = Registry()
        test_context = TestContext()
        name = str(uuid.uuid4())
        unknown_event = get_event(
            CONTAINER,
            CREATE,
            name,
            {
                CPU_LABEL_KEY: "1",
                NAME: name
            })
        event_handlers = test_context.get_event_handlers()
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, event_handlers, DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: test_context.get_create_event_handler().get_ignored_event_count() == 1)
        self.assertEqual(0, manager.get_queue_depth())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, len(test_context.get_event_handlers())))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, 1))

    def test_unknown_workload_type_label(self):
        registry = Registry()
        test_context = TestContext()
        unknown_event = get_event(
            CONTAINER,
            CREATE,
            uuid.uuid4(),
            {
                NAME: "container-name",
                APP_NAME_LABEL_KEY: DEFAULT_TEST_APP_NAME,
                CPU_LABEL_KEY: "1",
                MEM_LABEL_KEY: str(DEFAULT_TEST_MEM),
                DISK_LABEL_KEY: str(DEFAULT_TEST_DISK),
                NETWORK_LABEL_KEY: str(DEFAULT_TEST_NETWORK),
                JOB_TYPE_LABEL_KEY: DEFAULT_TEST_JOB_TYPE,
                WORKLOAD_TYPE_LABEL_KEY: "unknown",
                OWNER_EMAIL_LABEL_KEY: DEFAULT_TEST_OWNER_EMAIL,
                IMAGE_LABEL_KEY: DEFAULT_TEST_IMAGE,
            })
        valid_event = get_container_create_event(1)
        event_iterable = MockEventProvider([unknown_event, valid_event])
        manager = EventManager(
            event_iterable,
            test_context.get_event_handlers(),
            DEFAULT_TEST_EVENT_TIMEOUT_SECS)
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: manager.get_error_count() == 1)
        wait_until(lambda: manager.get_processed_count() == 2)
        self.assertEqual(0, manager.get_queue_depth())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, 5))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 1))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, 2))

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
        manager.set_registry(registry)
        manager.start_processing_events()

        wait_until(lambda: event_count == manager.get_processed_count())
        self.assertEqual(0, manager.get_queue_depth())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(0, test_context.get_create_event_handler().get_handled_event_count())
        self.assertEqual(0, test_context.get_free_event_handler().get_handled_event_count())
        self.assertEqual(1, test_context.get_rebalance_event_handler().get_handled_event_count())

        manager.stop_processing_events()

        manager.report_metrics({})
        self.assertTrue(gauge_value_equals(registry, QUEUE_DEPTH_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_SUCCEEDED_KEY, event_count * len(test_context.get_event_handlers())))
        self.assertTrue(gauge_value_equals(registry, EVENT_FAILED_KEY, 0))
        self.assertTrue(gauge_value_equals(registry, EVENT_PROCESSED_KEY, event_count))
