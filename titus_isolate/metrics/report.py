import logging

from spectator import GlobalRegistry

from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations

registry = GlobalRegistry
log = logging.getLogger()

SUCCEEDED_KEY = 'titus-isolate.succeeded'
FAILED_KEY = 'titus-isolate.failed'
QUEUE_DEPTH_KEY = 'titus-isolate.queueDepth'
PACKAGE_VIOLATIONS_KEY = 'titus-isolate.crossPackageViolations'
CORE_VIOLATIONS_KEY = 'titus-isolate.sharedCoreViolations'


def report_metrics(workload_manager):
    log.debug("Reporting metrics")
    try:
        # Workload manager metrics
        registry.gauge(SUCCEEDED_KEY).set(workload_manager.get_success_count())
        registry.gauge(FAILED_KEY).set(workload_manager.get_error_count())
        registry.gauge(QUEUE_DEPTH_KEY).set(workload_manager.get_queue_depth())

        # CPU metrics
        cross_package_violation_count = len(get_cross_package_violations(workload_manager.get_cpu()))
        shared_core_violation_count = len(get_shared_core_violations(workload_manager.get_cpu()))
        registry.gauge(PACKAGE_VIOLATIONS_KEY).set(cross_package_violation_count)
        registry.gauge(CORE_VIOLATIONS_KEY).set(shared_core_violation_count)
        log.debug("Reported metrics")

    except:
        log.exception("Failed to report metric")


def override_registry(reg):
    global registry
    registry = reg
