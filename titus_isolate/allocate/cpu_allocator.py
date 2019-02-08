import abc

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class CpuAllocator(abc.ABC, MetricsReporter):

    @abc.abstractmethod
    def assign_threads(self, cpu, workload):
        pass

    @abc.abstractmethod
    def free_threads(self, cpu, workload_id):
        pass

    def str(self):
        return self.__class__.__name__
