import copy

from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.metrics.pmc_subscriber import PmcSubscriber
from titus_isolate.utils import get_logger

log = get_logger()


class AtlasPmcSubscriber(PmcSubscriber, MetricsReporter):
    def __init__(self):
        super().__init__()
        self.__reg = None

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        q = copy.deepcopy(self.q)
        while len(q) > 0:
            metric = q.pop()
            log.info("Reporting PMC metric: {}".format(metric))

