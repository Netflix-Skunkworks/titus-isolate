from titus_isolate import log
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.cgroup.utils import set_cpuset, set_quota


class FileCgroupManager(CgroupManager):

    def set_cpuset(self, container_name, thread_ids):
        thread_ids_str = self.__get_thread_ids_str(thread_ids)
        log.info("updating workload: '{}' to cpuset.cpus: '{}'".format(container_name, thread_ids_str))
        set_cpuset(container_name, thread_ids_str)

    def set_quota(self, container_name, value):
        log.info("updating workload: '{}' to cpu.cfs_quota_us: '{}'".format(container_name, value))
        set_quota(container_name, value)

    @staticmethod
    def __get_thread_ids_str(thread_ids):
        return ",".join([str(t_id) for t_id in thread_ids])
