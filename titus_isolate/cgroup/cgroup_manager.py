from abc import abstractmethod


class CgroupManager:

    @abstractmethod
    def set_cpuset(self, container_name, thread_ids):
        pass

    @abstractmethod
    def set_quota(self, container_name, thread_ids):
        pass
