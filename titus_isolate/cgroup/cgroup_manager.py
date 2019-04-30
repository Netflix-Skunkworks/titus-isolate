from abc import abstractmethod

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class CgroupManager(MetricsReporter):

    @abstractmethod
    def set_cpuset(self, container_name, thread_ids):
        pass

    @abstractmethod
    def get_cpuset(self, container_name):
        pass

    @abstractmethod
    def release_cpuset(self, container_name):
        pass

    @abstractmethod
    def get_isolated_workload_ids(self):
        pass

    @abstractmethod
    def has_pending_work(self):
        pass
