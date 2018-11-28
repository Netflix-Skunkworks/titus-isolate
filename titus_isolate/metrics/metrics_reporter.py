import os
import time
from threading import Thread

import schedule as schedule
from spectator import GlobalRegistry

from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.utils import get_logger

registry = GlobalRegistry
log = get_logger()

ADDED_KEY = 'titus-isolate.added'
REMOVED_KEY = 'titus-isolate.removed'
REBALANCED_KEY = 'titus-isolate.rebalanced'
REBALANCED_NOOP_KEY = 'titus-isolate.rebalancedNoop'
SUCCEEDED_KEY = 'titus-isolate.succeeded'
FAILED_KEY = 'titus-isolate.failed'
QUEUE_DEPTH_KEY = 'titus-isolate.queueDepth'
WORKLOAD_COUNT_KEY = 'titus-isolate.workloadCount'

PACKAGE_VIOLATIONS_KEY = 'titus-isolate.crossPackageViolations'
CORE_VIOLATIONS_KEY = 'titus-isolate.sharedCoreViolations'


class MetricsReporter:
    def __init__(self, workload_manager, event_manager, reg=registry, report_interval=30, sleep_interval=1):
        self.__workload_manager = workload_manager
        self.__event_manager = event_manager
        self.__reg = reg
        self.__sleep_interval = sleep_interval
        schedule.every(report_interval).seconds.do(self.__report_metrics)

        self.__worker_thread = Thread(target=self.__schedule_loop)
        self.__worker_thread.daemon = True
        self.__worker_thread.start()

    def __schedule_loop(self):
        while True:
            schedule.run_pending()
            time.sleep(self.__sleep_interval)

    def __report_metrics(self):
        log.debug("Reporting metrics")
        try:
            tags = self.__get_tags()

            # Workload manager metrics
            self.__reg.gauge(ADDED_KEY, tags).set(self.__workload_manager.get_added_count())
            self.__reg.gauge(REMOVED_KEY, tags).set(self.__workload_manager.get_removed_count())
            self.__reg.gauge(REBALANCED_KEY, tags).set(self.__workload_manager.get_rebalanced_count())
            self.__reg.gauge(REBALANCED_NOOP_KEY, tags).set(self.__workload_manager.get_rebalanced_noop_count())
            self.__reg.gauge(SUCCEEDED_KEY, tags).set(self.__workload_manager.get_success_count())
            self.__reg.gauge(FAILED_KEY, tags).set(self.__workload_manager.get_error_count())
            self.__reg.gauge(QUEUE_DEPTH_KEY, tags).set(self.__event_manager.get_queue_depth())
            self.__reg.gauge(WORKLOAD_COUNT_KEY, tags).set(len(self.__workload_manager.get_workloads()))

            # CPU metrics
            cross_package_violation_count = len(get_cross_package_violations(self.__workload_manager.get_cpu()))
            shared_core_violation_count = len(get_shared_core_violations(self.__workload_manager.get_cpu()))
            self.__reg.gauge(PACKAGE_VIOLATIONS_KEY, tags).set(cross_package_violation_count)
            self.__reg.gauge(CORE_VIOLATIONS_KEY, tags).set(shared_core_violation_count)
            log.debug("Reported metrics")

        except:
            log.exception("Failed to report metric")

    @staticmethod
    def __get_tags():
        ec2_instance_id = 'EC2_INSTANCE_ID'

        tags = {}
        if ec2_instance_id in os.environ:
            tags["node"] = os.environ[ec2_instance_id]

        return tags


def override_registry(reg):
    global registry
    registry = reg
