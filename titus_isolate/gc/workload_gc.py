import schedule

from titus_isolate import log
from titus_isolate.config.constants import DEFAULT_WORKLOAD_GC_INTERVAL_SEC
from titus_isolate.docker.utils import get_current_workloads
from titus_isolate.metrics.constants import WORKLOAD_GC_COUNT_KEY
from titus_isolate.metrics.metrics_reporter import MetricsReporter


class WorkloadGarbageCollector(MetricsReporter):

    def __init__(self, workload_manager, docker_client, gc_interval=DEFAULT_WORKLOAD_GC_INTERVAL_SEC):
        self.__workload_manager = workload_manager
        self.__docker_client = docker_client
        self.__reg = None
        self.__workloads_garbage_collected = 0

        schedule.every(gc_interval).seconds.do(self._gc_workloads)

    def _gc_workloads(self):
        orphaned_ids = self._get_orphaned_workload_ids()
        log.error("Garbage collecting orphaned workloads: '{}'".format(orphaned_ids))

        # We count garbage collection events early, so we cannot possibly fail to report due to errors below.
        self.__workloads_garbage_collected += len(orphaned_ids)

        for id in orphaned_ids:
            self.__workload_manager.remove_workload(id)

    def _get_orphaned_workload_ids(self):
        wm_workload_ids = set([workload.get_id() for workload in self.__workload_manager.get_workloads()])
        current_workload_ids = set([workload.get_id() for workload in get_current_workloads(self.__docker_client)])
        return wm_workload_ids - current_workload_ids

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(WORKLOAD_GC_COUNT_KEY, tags).set(self.__workloads_garbage_collected)
