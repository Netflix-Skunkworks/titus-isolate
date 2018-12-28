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
        self.q.clear()
        while len(q) > 0:
            metric = q.pop()
            name = self.___get_metric_name(metric)
            tags = self.__update_tags(tags, metric)
            log.debug("Reporting PMC metric, name: {}, value: {}, tags: {}".format(name, metric.get_value(), tags))
            self.__reg.gauge(name, tags).set(metric.get_value())

    @staticmethod
    def ___get_metric_name(titus_pmc_metric):
        return "titus-isolate.{}".format(titus_pmc_metric.get_name())

    @staticmethod
    def __update_tags(tags, titus_pmc_metric):
        tags_copy = copy.deepcopy(tags)
        tags_copy["timestamp"] = str(titus_pmc_metric.get_timestamp())
        tags_copy["duration"] = str(titus_pmc_metric.get_duration())
        tags_copy["cpu_id"] = str(titus_pmc_metric.get_cpu_id())
        tags_copy["job_id"] = str(titus_pmc_metric.get_job_id())
        tags_copy["task_id"] = str(titus_pmc_metric.get_task_id())
        return tags_copy
