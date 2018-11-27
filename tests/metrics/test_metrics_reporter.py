import logging
import unittest
import uuid

from spectator import Registry

from tests.cgroup.mock_cgroup_manager import MockCgroupManager
from tests.utils import wait_until, config_logs
from titus_isolate.docker.constants import STATIC
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.metrics_reporter import ADDED_KEY, SUCCEEDED_KEY, FAILED_KEY, PACKAGE_VIOLATIONS_KEY, \
    CORE_VIOLATIONS_KEY, override_registry, MetricsReporter, REMOVED_KEY, REBALANCED_KEY, \
    REBALANCED_NOOP_KEY, WORKLOAD_COUNT_KEY
from titus_isolate.model.processor.config import get_cpu
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_logger

config_logs(logging.DEBUG)
log = get_logger(logging.DEBUG)


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
        workload_manager = WorkloadManager(get_cpu(), MockCgroupManager())

        MetricsReporter(workload_manager, registry, 0.01, 0.01)

        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_NOOP_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, WORKLOAD_COUNT_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))

        workload_manager.add_workload(workload)
        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_NOOP_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 2))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, WORKLOAD_COUNT_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))

        workload_manager.remove_workload(workload.get_id())
        wait_until(lambda: self.__gauge_value_reached(registry, ADDED_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, REMOVED_KEY, 1))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, REBALANCED_NOOP_KEY, 2))
        wait_until(lambda: self.__gauge_value_reached(registry, SUCCEEDED_KEY, 4))
        wait_until(lambda: self.__gauge_value_reached(registry, FAILED_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, WORKLOAD_COUNT_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, PACKAGE_VIOLATIONS_KEY, 0))
        wait_until(lambda: self.__gauge_value_reached(registry, CORE_VIOLATIONS_KEY, 0))
