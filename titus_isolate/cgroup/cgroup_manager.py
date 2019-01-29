from abc import abstractmethod

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class CgroupManager(MetricsReporter):

    @abstractmethod
    def set_cpuset(self, container_name, thread_ids):
        pass
