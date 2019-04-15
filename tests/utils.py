import logging
import time

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.config.test_property_provider import TestPropertyProvider
from tests.test_event_log_manager import TestEventLogManager
from titus_isolate import LOG_FMT_STRING, log
from titus_isolate.allocate.integer_program_cpu_allocator import IntegerProgramCpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.event.create_event_handler import CreateEventHandler
from titus_isolate.event.free_event_handler import FreeEventHandler
from titus_isolate.event.rebalance_event_handler import RebalanceEventHandler
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload
from titus_isolate.utils import set_config_manager

DEFAULT_TIMEOUT_SECONDS = 3
DEFAULT_TEST_MEM = 256
DEFAULT_TEST_DISK = 512
DEFAULT_TEST_NETWORK = 1024
DEFAULT_TEST_APP_NAME = 'test_app_name'
DEFAULT_TEST_OWNER_EMAIL = 'user@email.org'
DEFAULT_TEST_IMAGE = 'test_image'
DEFAULT_TEST_CMD = 'test_cmd'
DEFAULT_TEST_ENTRYPOINT = 'test_entrypoint'
DEFAULT_TEST_JOB_TYPE = 'SERVICE'
DEFAULT_TEST_INSTANCE_ID = 'test_instance_id'

set_config_manager(ConfigManager(TestPropertyProvider({})))


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


def get_threads_with_workload(cpu, workload_id):
    return [t for t in cpu.get_threads() if workload_id in t.get_workload_ids()]


def get_test_workload(identifier, thread_count, workload_type):
    return Workload(
        identifier=identifier,
        thread_count=thread_count,
        mem=DEFAULT_TEST_MEM,
        disk=DEFAULT_TEST_DISK,
        network=-DEFAULT_TEST_NETWORK,
        app_name=DEFAULT_TEST_APP_NAME,
        owner_email=DEFAULT_TEST_OWNER_EMAIL,
        image=DEFAULT_TEST_IMAGE,
        command=DEFAULT_TEST_CMD,
        entrypoint=DEFAULT_TEST_ENTRYPOINT,
        job_type=DEFAULT_TEST_JOB_TYPE,
        workload_type=workload_type)


def config_logs(level):
    logging.basicConfig(
        format=LOG_FMT_STRING,
        datefmt='%d-%m-%Y:%H:%M:%S',
        level=level)


class TestContext:
    def __init__(self, cpu=None, allocator=IntegerProgramCpuAllocator()):
        if cpu is None:
            cpu = get_cpu()
        self.__workload_manager = WorkloadManager(cpu, MockCgroupManager(), allocator, TestEventLogManager())
        self.__create_event_handler = CreateEventHandler(self.__workload_manager)
        self.__free_event_handler = FreeEventHandler(self.__workload_manager)
        self.__rebalance_event_handler = RebalanceEventHandler(self.__workload_manager)

    def get_cpu(self):
        return self.__workload_manager.get_cpu()

    def get_workload_manager(self):
        return self.__workload_manager

    def get_create_event_handler(self):
        return self.__create_event_handler

    def get_free_event_handler(self):
        return self.__free_event_handler

    def get_rebalance_event_handler(self):
        return self.__rebalance_event_handler

    def get_event_handlers(self):
        return [self.__create_event_handler, self.__free_event_handler, self.__rebalance_event_handler]


