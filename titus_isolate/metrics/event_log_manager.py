from abc import abstractmethod

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class EventLogManager(MetricsReporter):

    @abstractmethod
    def report_event(self, payload: dict):
        pass
