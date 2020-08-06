from abc import abstractmethod
from datetime import datetime

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class OpportunisticWindowPublisher(MetricsReporter):

    @abstractmethod
    def is_window_active(self) -> bool:
        pass

    @abstractmethod
    def add_window(self, start: datetime, end: datetime, free_cpu_count: int):
        pass

    @abstractmethod
    def cleanup(self):
        pass
