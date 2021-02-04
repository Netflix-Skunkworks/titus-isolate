from typing import List

from titus_isolate import log
from titus_isolate.monitor.resource_usage import ResourceUsage
from titus_isolate.monitor.resource_usage_provider import ResourceUsageProvider


class NoopResourceUsageProvider(ResourceUsageProvider):

    def get_resource_usages(self, workload_ids: List[str]) -> List[ResourceUsage]:
        log.info("noop resource usage provider returning empty result")
        return []
