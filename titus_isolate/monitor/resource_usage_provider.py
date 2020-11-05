from abc import abstractmethod
from typing import List

from titus_isolate.monitor.resource_usage import ResourceUsage


class ResourceUsageProvider:

    @abstractmethod
    def get_resource_usages(self) -> List[ResourceUsage]:
        pass
