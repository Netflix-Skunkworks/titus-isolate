import time
import unittest
import uuid

from tests.docker.mock_docker import get_container_create_event, MockDockerClient, MockEventProvider, get_event, \
    get_container_die_event
from titus_isolate.docker.constants import CONTAINER, CREATE
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.docker.free_event_handler import FreeEventHandler
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.model.processor.utils import get_cpu, DEFAULT_TOTAL_THREAD_COUNT

DEFAULT_CPU_COUNT = 2


def get_event_handlers(cpu):
    resource_manager = ResourceManager(cpu, MockDockerClient())
    create_event_handler = CreateEventHandler(resource_manager)
    free_event_handler = FreeEventHandler(resource_manager)
    return [EventLogger(), create_event_handler, free_event_handler]


def get_create_event_handler(event_handlers):
    return event_handlers[1]


def get_free_event_handler(event_handlers):
    return event_handlers[2]


class TestDocker(unittest.TestCase):

    def test_update_mock_container(self):
        event_iterable = MockEventProvider([get_container_create_event(DEFAULT_CPU_COUNT)])
        cpu = get_cpu()
        event_handlers = get_event_handlers(cpu)
        manager = EventManager(event_iterable, event_handlers)

        self.__wait_until_events_processed(manager, 30, 1)
        self.assertEqual(1, get_create_event_handler(event_handlers).get_handled_event_count())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT - DEFAULT_CPU_COUNT, len(cpu.get_empty_threads()))

        manager.stop_processing_events()

    def test_unknown_action(self):
        unknown_event = get_event(CONTAINER, "unknown", uuid.uuid4(), {})
        event_handlers = get_event_handlers(get_cpu())
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, event_handlers)

        self.__wait_until_events_ignored(get_create_event_handler(event_handlers), 30, 1)

        manager.stop_processing_events()

    def test_absent_cpu_label(self):
        unknown_event = get_event(CONTAINER, CREATE, uuid.uuid4(), {})
        event_handlers = get_event_handlers(get_cpu())
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, event_handlers)

        self.__wait_until_events_ignored(get_create_event_handler(event_handlers), 30, 1)

        manager.stop_processing_events()

    def test_free_cpu_on_container_die(self):
        container_name = "container_name"
        cpu = get_cpu()
        event_handlers = get_event_handlers(cpu)
        events = [
            get_container_create_event(DEFAULT_CPU_COUNT, container_name),
            get_container_die_event(container_name)]
        event_iterable = MockEventProvider(events)
        manager = EventManager(event_iterable, event_handlers)

        self.__wait_until_events_processed(manager, 30, 2)
        self.assertEqual(1, get_create_event_handler(event_handlers).get_handled_event_count())
        self.assertEqual(1, get_free_event_handler(event_handlers).get_handled_event_count())
        self.assertEqual(DEFAULT_TOTAL_THREAD_COUNT, len(cpu.get_empty_threads()))

        manager.stop_processing_events()

    @staticmethod
    def __wait_until_events_processed(event_manager, timeout, event_count=1, period=0.1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if event_manager.get_processed_event_count() >= event_count:
                return
            time.sleep(period)

        raise TimeoutError(
            "Expected number of events: '{}' not encountered within timeout: '{}'.".format(event_count, timeout))

    @staticmethod
    def __wait_until_events_ignored(event_handler, timeout, event_count=1, period=0.1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if event_handler.get_ignored_event_count() >= event_count:
                return
            time.sleep(period)

        raise TimeoutError(
            "Expected number of events: '{}' not encountered within timeout: '{}'.".format(event_count, timeout))
