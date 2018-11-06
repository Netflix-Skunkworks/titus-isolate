import logging
import unittest
import uuid

from spectator import Registry

from tests.docker.mock_docker import MockDockerClient, MockContainer
from tests.utils import wait_until
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.metrics_reporter import SUCCEEDED_KEY, FAILED_KEY, PACKAGE_VIOLATIONS_KEY, \
    CORE_VIOLATIONS_KEY, QUEUE_DEPTH_KEY, override_registry, MetricsReporter
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)
log = logging.getLogger()


class TestMetricsReporter(unittest.TestCase):

    @staticmethod
    def __gauge_value_reached(registry, key, expected_value):
        value = registry.gauge(key).get()
        log.debug("gauge: '{}'='{}' expected: '{}'".format(key, value, expected_value))
        return value == expected_value

    def test_report_metrics(self):
        registry = Registry()
        override_registry(registry)
        thread_count = 2
        workload = Workload(uuid.uuid4(), thread_count, STATIC)
        docker_client = MockDockerClient([MockContainer(workload)])
        workload_manager = WorkloadManager(get_cpu(), docker_client)

        MetricsReporter(workload_manager, registry, 0.01, 0.01)

        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))

        workload_manager.add_workloads([workload])
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 2))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, QUEUE_DEPTH_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))
