from abc import abstractmethod
from datetime import datetime

from titus_isolate.metrics.metrics_reporter import MetricsReporter


class OpportunisticWindowPublisher(MetricsReporter):

    @abstractmethod
    def get_current_end(self) -> datetime:
        pass

    @abstractmethod
    def add_window(self, start: datetime, end: datetime, free_cpu_count: int):
        pass
