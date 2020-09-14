from abc import abstractmethod
from typing import List

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class CgroupManager(MetricsReporter):

    @abstractmethod
    def set_cpuset(self, container_name: str, thread_ids: List[int]):
        pass

    @abstractmethod
    def get_cpuset(self, container_name: str) -> List[int]:
        pass

    @abstractmethod
    def set_quota(self, container_name: str, quota: int):
        pass

    @abstractmethod
    def get_quota(self, container_name: str) -> int:
        pass

    @abstractmethod
    def set_shares(self, container_name: str, shares: int):
        pass

    @abstractmethod
    def get_shares(self, container_name) -> int:
        pass

    @abstractmethod
    def set_memory_migrate(self, container_name, on: bool):
        pass

    @abstractmethod
    def get_memory_migrate(self, container_name) -> bool:
        pass

    @abstractmethod
    def set_memory_spread_page(self, container_name, on: bool):
        pass

    @abstractmethod
    def get_memory_spread_page(self, container_name) -> bool:
        pass

    @abstractmethod
    def set_memory_spread_slab(self, container_name, on: bool):
        pass

    @abstractmethod
    def get_memory_spread_slab(self, container_name) -> bool:
        pass

    @abstractmethod
    def release_container(self, container_name):
        pass

    @abstractmethod
    def get_isolated_workload_ids(self) -> List[str]:
        pass

    @abstractmethod
    def has_pending_work(self) -> bool:
        pass
