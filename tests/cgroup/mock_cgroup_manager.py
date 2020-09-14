from titus_isolate import log
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.config.constants import DEFAULT_TITUS_ISOLATE_MEMORY_MIGRATE, \
    DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_PAGE, DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_SLAB


class MockCgroupManager(CgroupManager):
    def __init__(self):
        self.container_update_map = {}
        self.container_update_counts = {}
        self.__memory_migrate = DEFAULT_TITUS_ISOLATE_MEMORY_MIGRATE
        self.__memory_spread_page = DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_PAGE
        self.__memory_spread_slab = DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_SLAB

    def set_cpuset(self, container_name, thread_ids):
        log.debug("Updating container: '{}' to cpuset: '{}'".format(container_name, thread_ids))
        self.container_update_map[container_name] = thread_ids

        if container_name not in self.container_update_counts:
            self.container_update_counts[container_name] = 1
        else:
            self.container_update_counts[container_name] += 1

    def get_cpuset(self, container_name):
        return self.container_update_map.get(container_name, [])

    def set_quota(self, container_name: str, quota: int):
        pass

    def get_quota(self, container_name: str) -> int:
        pass

    def set_shares(self, container_name: str, shares: int):
        pass

    def get_shares(self, container_name) -> int:
        pass

    def set_memory_migrate(self, container_name, on: bool):
        self.__memory_migrate = on

    def get_memory_migrate(self, container_name) -> bool:
        return self.__memory_migrate

    def set_memory_spread_page(self, container_name, on: bool):
        self.__memory_spread_page = on

    def get_memory_spread_page(self, container_name) -> bool:
        return self.__memory_spread_page

    def set_memory_spread_slab(self, container_name, on: bool):
        self.__memory_spread_slab = on

    def get_memory_spread_slab(self, container_name) -> bool:
        return self.__memory_spread_slab

    def release_container(self, container_name):
        if container_name in self.container_update_map:
            self.container_update_map.pop(container_name)

    def get_isolated_workload_ids(self):
        return list(self.container_update_map.keys())

    def has_pending_work(self):
        return False

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
