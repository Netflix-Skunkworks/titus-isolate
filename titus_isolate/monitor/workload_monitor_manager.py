import json
from threading import Lock
from typing import List

from titus_isolate import log
from titus_isolate.monitor.resource_usage import GlobalResourceUsage
from titus_isolate.monitor.resource_usage_provider import ResourceUsageProvider
from titus_isolate.monitor.utils import resource_usages_to_dict


class WorkloadMonitorManager:

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
            log.error("failed to get resource usage, returning empty usage")
            with self.__metric_lock:
                self.__get_resource_usage_failure_count += 1
            return GlobalResourceUsage({})

    def set_registry(self, registry, tags):
        self.__registry = registry
