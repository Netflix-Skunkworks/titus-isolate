import logging
import time
from unittest.mock import MagicMock

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.docker.mock_docker import MockDockerClient
from titus_isolate import LOG_FMT_STRING
from titus_isolate.cgroup.file_manager import FileManager
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.free_event_handler import FreeEventHandler
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu


DEFAULT_TIMEOUT_SECONDS = 3


def wait_until(func, timeout=DEFAULT_TIMEOUT_SECONDS, period=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if func():
            return
        time.sleep(period)

    raise TimeoutError(
        "Function did not succeed within timeout: '{}'.".format(timeout))


def config_logs(level):
    logging.basicConfig(
        format=LOG_FMT_STRING,
        datefmt='%d-%m-%Y:%H:%M:%S',
        level=level)


def get_mock_file_manager():
    file_manager = FileManager()
    file_manager.wait_for_files = MagicMock(return_value=True)
    return file_manager


class TestContext:
    def __init__(self, docker_client=MockDockerClient(), cpu=None):
        if cpu is None:
            cpu = get_cpu()
        self.__docker_client = docker_client
        self.__workload_manager = WorkloadManager(cpu, MockCgroupManager())
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


