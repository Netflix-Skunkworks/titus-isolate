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

