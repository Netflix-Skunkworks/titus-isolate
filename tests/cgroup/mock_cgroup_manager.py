from titus_isolate import log
from titus_isolate.cgroup.cgroup_manager import CgroupManager


class MockCgroupManager(CgroupManager):

    def __init__(self):
        self.container_update_map = {}
        self.container_update_counts = {}

    def set_cpuset(self, container_name, thread_ids):
        log.debug("Updating container: '{}' to cpuset: '{}'".format(container_name, thread_ids))
        self.container_update_map[container_name] = thread_ids

        if container_name not in self.container_update_counts:
            self.container_update_counts[container_name] = 1
        else:
            self.container_update_counts[container_name] += 1

    def get_cpuset(self, container_name):
        return self.container_update_map.get(container_name, [])

    def release_cpuset(self, container_name):
        if container_name in self.container_update_map:
            self.container_update_map.pop(container_name)

    def get_isolated_workload_ids(self):
        return list(self.container_update_map.keys())

    def has_pending_work(self):
        return False

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
