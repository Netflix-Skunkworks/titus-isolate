import logging
import unittest
import uuid

from tests.docker.mock_docker import get_container_create_event, MockDockerClient, MockEventProvider, get_event, \
    get_container_die_event, MockContainer
from tests.utils import wait_until
from titus_isolate.docker.constants import CONTAINER, CREATE, STATIC, CPU_LABEL_KEY, WORKLOAD_TYPE_LABEL_KEY, NAME
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.docker.free_event_handler import FreeEventHandler
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.processor.utils import DEFAULT_TOTAL_THREAD_COUNT
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_logger

DEFAULT_CPU_COUNT = 2

log = get_logger(logging.DEBUG)


class TestContext:
    def __init__(self, docker_client=MockDockerClient()):
        cpu = get_cpu()
        self.__docker_client = docker_client
        self.__workload_manager = WorkloadManager(cpu, self.__docker_client)
        self.__event_logger = EventLogger()
        self.__create_event_handler = CreateEventHandler(self.__workload_manager)
        self.__free_event_handler = FreeEventHandler(self.__workload_manager)

    def get_cpu(self):
        return self.__workload_manager.get_cpu()

    def get_docker_client(self):
        return self.__docker_client

    def get_workload_manager(self):
        return self.__workload_manager

    def get_create_event_handler(self):
        return self.__create_event_handler

    def get_free_event_handler(self):
        return self.__free_event_handler

    def get_event_handlers(self):
        return [self.__event_logger, self.__create_event_handler, self.__free_event_handler]


class TestEvents(unittest.TestCase):

    def test_update_mock_container(self):
        workload_name = str(uuid.uuid4())
        workload = Workload(workload_name, DEFAULT_CPU_COUNT, STATIC)
        docker_client = MockDockerClient([MockContainer(workload)])

        event_iterable = MockEventProvider(
            [get_container_create_event(DEFAULT_CPU_COUNT, STATIC, workload_name, workload_name)])

        test_context = TestContext(docker_client)
        manager = EventManager(event_iterable, test_context.get_event_handlers())

        wait_until(lambda: manager.get_processed_event_count() == 1)
        wait_until(lambda: test_context.get_workload_manager().get_success_count() > 0)
        wait_until(lambda: DEFAULT_TOTAL_THREAD_COUNT - DEFAULT_CPU_COUNT == len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(1, test_context.get_create_event_handler().get_handled_event_count())

        manager.stop_processing_events()

    def test_free_cpu_on_container_die(self):
        workload_name = str(uuid.uuid4())
        workload = Workload(workload_name, DEFAULT_CPU_COUNT, STATIC)
        docker_client = MockDockerClient([MockContainer(workload)])

        event_iterable = MockEventProvider([
            get_container_create_event(DEFAULT_CPU_COUNT, STATIC, workload_name, workload_name),
            get_container_die_event(workload_name)])

        test_context = TestContext(docker_client)
        manager = EventManager(event_iterable, test_context.get_event_handlers())

        wait_until(lambda: manager.get_processed_event_count() == 2)
        wait_until(lambda: test_context.get_workload_manager().get_success_count() > 0)
        wait_until(lambda: DEFAULT_TOTAL_THREAD_COUNT == len(test_context.get_cpu().get_empty_threads()))
        self.assertEqual(1, test_context.get_create_event_handler().get_handled_event_count())
        self.assertEqual(1, test_context.get_free_event_handler().get_handled_event_count())

        manager.stop_processing_events()

    def test_unknown_action(self):
        test_context = TestContext()
        unknown_event = get_event(CONTAINER, "unknown", uuid.uuid4(), {})
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, test_context.get_event_handlers())

        wait_until(lambda: test_context.get_create_event_handler().get_ignored_event_count() == 1)

        manager.stop_processing_events()

    def test_absent_cpu_label(self):
        test_context = TestContext()
        unknown_event = get_event(CONTAINER, CREATE, "unknown", {WORKLOAD_TYPE_LABEL_KEY: STATIC})
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, test_context.get_event_handlers())

        wait_until(lambda: test_context.get_create_event_handler().get_ignored_event_count() == 1)

        manager.stop_processing_events()

    def test_absent_workload_type_label(self):
        test_context = TestContext()
        unknown_event = get_event(CONTAINER, CREATE, uuid.uuid4(), {CPU_LABEL_KEY: "1"})
        event_handlers = test_context.get_event_handlers()
        event_iterable = MockEventProvider([unknown_event])
        manager = EventManager(event_iterable, event_handlers)

        wait_until(lambda: test_context.get_create_event_handler().get_ignored_event_count() == 1)

        manager.stop_processing_events()

    def test_unknown_workload_type_label(self):
        test_context = TestContext()
        unknown_event = get_event(
            CONTAINER,
            CREATE,
            uuid.uuid4(),
            {NAME: "container-name", CPU_LABEL_KEY: "1", WORKLOAD_TYPE_LABEL_KEY: "unknown"})
        valid_event = get_container_create_event(1)
        event_iterable = MockEventProvider([unknown_event, valid_event])
        manager = EventManager(event_iterable, test_context.get_event_handlers())

        wait_until(lambda: manager.get_error_event_count() == 1)
        wait_until(lambda: manager.get_processed_event_count() == 2)

        manager.stop_processing_events()

