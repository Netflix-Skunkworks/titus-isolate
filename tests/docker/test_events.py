import time
import unittest
import uuid

from tests.docker.mock_docker import get_container_create_event, MockDockerClient, MockEventProvider, get_event
from titus_isolate.docker.constants import CONTAINER, CREATE
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.model.processor.utils import get_cpu

DEFAULT_CPU_COUNT = 2
RESOURCE_MANAGER = ResourceManager(get_cpu(), MockDockerClient())
CREATE_EVENT_HANDLER = CreateEventHandler(RESOURCE_MANAGER)
EVENT_HANDLERS = [EventLogger(), CREATE_EVENT_HANDLER]


class TestDocker(unittest.TestCase):

    def test_update_mock_container(self):
        event_iterable = MockEventProvider([get_container_create_event(DEFAULT_CPU_COUNT)])
        manager = EventManager(event_iterable, EVENT_HANDLERS)
        self.__wait_until_events_processed(manager, 30, 1)
        self.assertEqual(1, CREATE_EVENT_HANDLER.get_handled_event_count())

        manager.stop_processing_events()

    def test_unknown_action(self):
        unknown_event = get_event(CONTAINER, "unknown", uuid.uuid4(), {})
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, EVENT_HANDLERS)
        self.__wait_until_events_ignored(CREATE_EVENT_HANDLER, 30, 1)

        manager.stop_processing_events()

    def test_absent_cpu_label(self):
        unknown_event = get_event(CONTAINER, CREATE, uuid.uuid4(), {})
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, EVENT_HANDLERS)
        self.__wait_until_events_ignored(CREATE_EVENT_HANDLER, 30, 1)

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
