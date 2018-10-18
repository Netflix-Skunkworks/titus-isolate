import time
import unittest

from tests.docker.mock_docker import get_container_create_event, MockDockerClient, MockEventProvider
from tests.utils import get_test_cpu
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.isolate.resource_manager import ResourceManager

DEFAULT_CPU_COUNT = 2
RESOURCE_MANAGER = ResourceManager(get_test_cpu(), MockDockerClient())
EVENT_HANDLERS = [EventLogger(), CreateEventHandler(RESOURCE_MANAGER)]


class TestDocker(unittest.TestCase):

    def test_update_mock_container(self):
        event_iterable = MockEventProvider([get_container_create_event(DEFAULT_CPU_COUNT)])
        manager = EventManager(event_iterable, EVENT_HANDLERS)
        self.__wait_until_events_processed(manager, 30, 1)

        manager.stop_processing_events()

    @staticmethod
    def __wait_until_events_processed(docker, timeout, event_count=1, period=0.1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if docker.get_processed_event_count() >= event_count:
                return
            time.sleep(period)

        raise TimeoutError(
            "Expected number of events: '{}' not encountered within timeout: '{}'.".format(event_count, timeout))
