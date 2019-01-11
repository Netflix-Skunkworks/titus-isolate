from titus_isolate import log
from titus_isolate.config.constants import CPU_ALLOCATORS
from titus_isolate.config.utils import get_cpu_allocator_index
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.metrics.metrics_reporter import MetricsReporter

ADDED_KEY = 'titus-isolate.added'
REMOVED_KEY = 'titus-isolate.removed'
SUCCEEDED_KEY = 'titus-isolate.succeeded'
FAILED_KEY = 'titus-isolate.failed'
QUEUE_DEPTH_KEY = 'titus-isolate.queueDepth'
WORKLOAD_COUNT_KEY = 'titus-isolate.workloadCount'
EVENT_SUCCEEDED_KEY = 'titus-isolate.eventSucceeded'
EVENT_FAILED_KEY = 'titus-isolate.eventFailed'
EVENT_PROCESSED_KEY = 'titus-isolate.eventProcessed'

PACKAGE_VIOLATIONS_KEY = 'titus-isolate.crossPackageViolations'
CORE_VIOLATIONS_KEY = 'titus-isolate.sharedCoreViolations'

CPU_ALLOCATOR_KEY = 'titus-isolate.cpu_allocator'


class InternalMetricsReporter(MetricsReporter):

    def __init__(self, workload_manager, event_manager):
        self.__workload_manager = workload_manager
        self.__event_manager = event_manager
        self.__reg = None

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        log.debug("Reporting metrics")
        try:
            # Workload manager metrics
            allocator_index = get_cpu_allocator_index(self.__workload_manager.get_allocator_name())
            self.__reg.gauge(CPU_ALLOCATOR_KEY, tags).set(allocator_index)

            self.__reg.gauge(ADDED_KEY, tags).set(self.__workload_manager.get_added_count())
            self.__reg.gauge(REMOVED_KEY, tags).set(self.__workload_manager.get_removed_count())
            self.__reg.gauge(SUCCEEDED_KEY, tags).set(self.__workload_manager.get_success_count())
            self.__reg.gauge(FAILED_KEY, tags).set(self.__workload_manager.get_error_count())
            self.__reg.gauge(WORKLOAD_COUNT_KEY, tags).set(len(self.__workload_manager.get_workloads()))

            # Event manager metrics
            self.__reg.gauge(QUEUE_DEPTH_KEY, tags).set(self.__event_manager.get_queue_depth())
            self.__reg.gauge(EVENT_SUCCEEDED_KEY, tags).set(self.__event_manager.get_success_count())
            self.__reg.gauge(EVENT_FAILED_KEY, tags).set(self.__event_manager.get_error_count())
            self.__reg.gauge(EVENT_PROCESSED_KEY, tags).set(self.__event_manager.get_processed_count())

            # CPU metrics
            cross_package_violation_count = len(get_cross_package_violations(self.__workload_manager.get_cpu()))
            shared_core_violation_count = len(get_shared_core_violations(self.__workload_manager.get_cpu()))
            self.__reg.gauge(PACKAGE_VIOLATIONS_KEY, tags).set(cross_package_violation_count)
            self.__reg.gauge(CORE_VIOLATIONS_KEY, tags).set(shared_core_violation_count)
            log.debug("Reported metrics")

        except:
            log.exception("Failed to report metric")
