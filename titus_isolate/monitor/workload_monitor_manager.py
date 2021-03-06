import json
from threading import Lock
from typing import List

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.metrics.constants import BURST_POOL_USAGE_KEY, STATIC_POOL_USAGE_KEY, GET_RESOURCE_USAGE_FAILURE
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.monitor.resource_usage import GlobalResourceUsage
from titus_isolate.monitor.resource_usage_provider import ResourceUsageProvider
from titus_isolate.monitor.utils import resource_usages_to_dict
from titus_isolate.utils import get_workload_manager


class WorkloadMonitorManager(MetricsReporter):

    def __init__(self, resource_usage_provider: ResourceUsageProvider):
        self.__resource_usage_provider = resource_usage_provider
        self.__registry = None
        self.__metric_lock = Lock()
        self.__get_resource_usage_failure_count = 0

    def __get_usage_dict(self, workload_ids: List[str]) -> dict:
        log.info("Getting resource usage from resource usage provider: %s", self.__resource_usage_provider.get_name())
        usages_dict = resource_usages_to_dict(self.__resource_usage_provider.get_resource_usages(workload_ids))
        return usages_dict

    def get_resource_usage(self, workload_ids: List[str]) -> GlobalResourceUsage:
        try:
            global_usage = GlobalResourceUsage(self.__get_usage_dict(workload_ids))
            log.debug("Got resource usage: %s", json.dumps(global_usage.serialize(), sort_keys=True, separators=(',', ':')))
            return global_usage
        except Exception:
            log.exception("failed to get resource usage, returning empty usage")
            with self.__metric_lock:
                self.__get_resource_usage_failure_count += 1
            return GlobalResourceUsage({})

    def set_registry(self, registry, tags):
        self.__registry = registry

    def report_metrics(self, tags):
        if self.__registry is None:
            log.debug("Not reporting metrics because there's no registry available yet.")
            return

        wm = get_workload_manager()
        if wm is None:
            log.debug("Not reporting metrics because there's no workload manager available yet.")
            return

        workload_ids = wm.get_workload_map_copy().keys()
        usage_dict = self.__get_usage_dict(workload_ids)
        if CPU_USAGE not in usage_dict.keys():
            log.warning("No CPU usage in usage: %s", usage_dict)
            return

        usage = usage_dict[CPU_USAGE]
        static_pool_cpu_usage = self.__get_pool_usage(STATIC, usage)
        burst_pool_cpu_usage = self.__get_pool_usage(BURST, usage)

        self.__registry.gauge(STATIC_POOL_USAGE_KEY, tags).set(static_pool_cpu_usage)
        self.__registry.gauge(BURST_POOL_USAGE_KEY, tags).set(burst_pool_cpu_usage)

        with self.__metric_lock:
            self.__registry.counter(GET_RESOURCE_USAGE_FAILURE, tags).increment(self.__get_resource_usage_failure_count)
            self.__get_resource_usage_failure_count = 0

    @staticmethod
    def __get_pool_usage(workload_type, usage):
        wm = get_workload_manager()
        if wm is None:
            log.debug("Not reporting metrics because there's no workload manager available yet.")
            return

        workload_map = wm.get_workload_map_copy()

        pool_cpu_usage = 0.0
        for w_id, usage in usage.items():
            if w_id not in workload_map:
                continue

            workload = workload_map[w_id]
            if workload.get_type() == workload_type:
                pool_cpu_usage += float(usage[len(usage) - 1])

        return pool_cpu_usage

    @staticmethod
    def __get_workloads():
        wm = get_workload_manager()
        if wm is None:
            log.debug("Workload manager not yet present.")
            return []

        return wm.get_workloads()
