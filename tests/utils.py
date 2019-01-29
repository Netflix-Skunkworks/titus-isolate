import logging
import time

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.docker.mock_docker import MockContainer
from titus_isolate import LOG_FMT_STRING, log
from titus_isolate.docker.constants import STATIC
from titus_isolate.docker.start_event_handler import StartEventHandler
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.free_event_handler import FreeEventHandler
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload

DEFAULT_TIMEOUT_SECONDS = 3


def wait_until(func, timeout=DEFAULT_TIMEOUT_SECONDS, period=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if func():
            return
        time.sleep(period)

    raise TimeoutError(
        "Function did not succeed within timeout: '{}'.".format(timeout))


def gauge_value_equals(registry, key, expected_value, tags={}):
    value = registry.gauge(key, tags).get()
    log.debug("gauge: '{}'='{}' expected: '{}'".format(key, value, expected_value))
    return value == expected_value


def gauge_value_reached(registry, key, min_expected_value):
    value = registry.gauge(key).get()
    log.debug("gauge: '{}'='{}' min expected: '{}'".format(key, value, min_expected_value))
    return value >= min_expected_value


def config_logs(level):
    logging.basicConfig(
        format=LOG_FMT_STRING,
        datefmt='%d-%m-%Y:%H:%M:%S',
        level=level)


def get_test_container(name, thread_count):
    return MockContainer(Workload(name, thread_count, STATIC))


class TestContext:
    def __init__(self, cpu=None):
        if cpu is None:
            cpu = get_cpu()
        self.__workload_manager = WorkloadManager(cpu, MockCgroupManager())
        self.__event_logger = EventLogger()
        self.__create_event_handler = StartEventHandler(self.__workload_manager)
        self.__free_event_handler = FreeEventHandler(self.__workload_manager)

    def get_cpu(self):
        return self.__workload_manager.get_cpu()

    def get_workload_manager(self):
        return self.__workload_manager

    def get_create_event_handler(self):
        return self.__create_event_handler

    def get_free_event_handler(self):
        return self.__free_event_handler

    def get_event_handlers(self):
        return [self.__event_logger, self.__create_event_handler, self.__free_event_handler]


