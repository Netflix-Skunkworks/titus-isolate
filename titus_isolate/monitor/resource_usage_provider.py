from abc import abstractmethod
from typing import List

from titus_isolate.monitor.resource_usage import ResourceUsage


class ResourceUsageProvider:

    @abstractmethod
    def get_resource_usages(self, workload_ids: List[str]) -> List[ResourceUsage]:
        pass

    @abstractmethod
    def get_name(self) -> str:
        return self.__class__.__name__
