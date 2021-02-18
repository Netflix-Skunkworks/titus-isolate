from threading import Thread, Lock

from titus_isolate import log
from titus_isolate.crd.publish.kubernetes_predicted_usage_publisher import KubernetesPredictedUsagePublisher
from titus_isolate.event.constants import ACTION, PREDICT_USAGE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.metrics.metrics_reporter import MetricsReporter

PUBLISH_SUCCESS_COUNT = 'titus-isolate.predictedUsagePublishSucceeded'
PUBLISH_FAILURE_COUNT = 'titus-isolate.predictedUsagePublishFailed'


class ResourceUsagePredictionHandler(EventHandler, MetricsReporter):

    def __init__(self, kubernetes_predicted_usage_publisher: KubernetesPredictedUsagePublisher):
        super().__init__()
        self.__publisher = kubernetes_predicted_usage_publisher
        self.__reg = None
        self.__publish_lock = Lock()
        self.__metric_lock = Lock()

        self.__publish_success_count = 0
        self.__publish_failure_count = 0

    def handle(self, event):
        Thread(target=self._handle, args=[event]).start()

    def _handle(self, event):
        try:
            if not self.__relevant(event):
                self.ignored_event(event, "irrelevant")
                return

            with self.__publish_lock:
                self.__publisher.publish()

            with self.__metric_lock:
                self.__publish_success_count += 1
        except Exception:
            with self.__metric_lock:
                self.__publish_failure_count += 1
            log.error("Failed to publish resource usage predictions")

    def __relevant(self, event):
        if not event[ACTION] == PREDICT_USAGE:
            self.ignored_event(event, 'not a {} event'.format(PREDICT_USAGE))
            return False

        return True

    def set_registry(self, registry, tags):
        self.__reg = registry
        self.__publisher.set_registry(registry, tags)

    def report_metrics(self, tags):
        with self.__metric_lock:
            self.__reg.counter(PUBLISH_SUCCESS_COUNT, tags).increment(self.__publish_success_count)
            self.__reg.counter(PUBLISH_FAILURE_COUNT, tags).increment(self.__publish_failure_count)
            self.__publish_success_count = 0
            self.__publish_failure_count = 0
            self.__publisher.report_metrics(tags)
