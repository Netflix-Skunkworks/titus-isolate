from abc import abstractmethod

from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu


class EventLogManager(MetricsReporter):

    @abstractmethod
    def report_cpu(self, cpu: Cpu, workloads: list):
        pass
