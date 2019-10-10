from abc import abstractmethod


class MetricsReporter:

    @abstractmethod
    def set_registry(self, registry, tags):
        pass

    @abstractmethod
    def report_metrics(self, tags):
        pass
