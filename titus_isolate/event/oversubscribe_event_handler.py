import json
from datetime import datetime, timedelta
from threading import Thread, Lock
from typing import Dict

from titus_isolate import log
from titus_isolate.config.constants import OVERSUBSCRIBE_WINDOW_SIZE_MINUTES_KEY, \
    DEFAULT_OVERSUBSCRIBE_WINDOW_SIZE_MINUTES, EC2_INSTANCE_ID, \
    DEFAULT_OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE, OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE_KEY, TOTAL_THRESHOLD, \
    DEFAULT_TOTAL_THRESHOLD
from titus_isolate.crd.publish.opportunistic_window_publisher import OpportunisticWindowPublisher
from titus_isolate.event.constants import ACTION, OVERSUBSCRIBE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import OVERSUBSCRIBE_FAIL_COUNT, OVERSUBSCRIBE_SKIP_COUNT, \
    OVERSUBSCRIBE_SUCCESS_COUNT
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.utils import get_duration
from titus_isolate.utils import get_config_manager, get_workload_monitor_manager, managers_are_initialized, \
    get_cpu_usage_predictor_manager

CRD_VERSION = 'apiextensions.k8s.io/v1beta1'
CRD_KIND = 'CustomResourceDefinition'


class OversubscribeEventHandler(EventHandler, MetricsReporter):

    def __init__(self,
                 workload_manager: WorkloadManager,
                 window_publisher: OpportunisticWindowPublisher):

        super().__init__()
        self.__workload_manager = workload_manager
        self.__window_publisher = window_publisher

        self.__reg = None
        self.__fail_count = 0
        self.__skip_count = 0
        self.__success_count = 0
        self.__reclaimed_cpu_count = None

        self.__config_manager = get_config_manager()
        self.__workload_monitor_manager = get_workload_monitor_manager()
        self.__cpu_usage_predictor_manager = get_cpu_usage_predictor_manager()

        self.__node_name = self.__config_manager.get_str(EC2_INSTANCE_ID)
        self.__window_end_time = self.__window_publisher.get_current_end()
        self.__window_lock = Lock()

    def set_registry(self, registry, tags):
        self.__reg = registry
        self.__window_publisher.set_registry(registry, tags)

    def report_metrics(self, tags):
        self.__reg.gauge(OVERSUBSCRIBE_FAIL_COUNT, tags).set(self.get_fail_count())
        self.__reg.gauge(OVERSUBSCRIBE_SKIP_COUNT, tags).set(self.get_skip_count())
        self.__reg.gauge(OVERSUBSCRIBE_SUCCESS_COUNT, tags).set(self.get_success_count())
        self.__window_publisher.report_metrics(tags)

    def get_fail_count(self):
        return self.__fail_count

    def get_skip_count(self):
        return self.__skip_count

    def get_success_count(self):
        return self.__success_count

    def get_reclaimed_cpu_count(self):
        return self.__reclaimed_cpu_count

    def handle(self, event):
        Thread(target=self._handle, args=[event]).start()

    def __get_simple_cpu_predictions(self) -> Dict[str, float]:
        cpu_predictor = self.__cpu_usage_predictor_manager.get_cpu_predictor()
        if cpu_predictor is None:
            log.error("Failed to get cpu predictor")
            return {}

        workloads = self.__workload_manager.get_workloads()
        if len(workloads) == 0:
            log.warning("No workloads, skipping cpu usage prediction")
            return {}

        workload_ids = [w.get_id() for w in workloads]
        resource_usage = self.__workload_monitor_manager.get_resource_usage(workload_ids)

        log.info("Getting simple cpu predictions...")
        cpu_predictions = cpu_predictor.get_cpu_predictions(workloads, resource_usage)
        if cpu_predictions is None:
            log.error("Failed to get cpu predictions")
            return {}
        else:
            log.info("Got simple cpu predictions: %s", json.dumps(cpu_predictions))
            return cpu_predictions

    def _handle(self, event):
        try:
            if not self.__relevant(event):
                return

            if not managers_are_initialized():
                log.warning("Managers are not yet initialized")
                return None

            self.handling_event(event, 'oversubscribing workloads')

            with self.__window_lock:
                if datetime.utcnow() < self.__window_end_time:
                    self.__skip_count += 1
                    self.handled_event(event, 'skipping oversubscribe - a window is currently active')
                    return

                self.__publish_window(event)

        except Exception:
            self.__fail_count += 1
            log.error("Event handler: '{}' failed to handle event: '{}'".format(
                self.__class__.__name__, event))

    def __publish_window(self, event):
        # we calculate the window before we send the request to ensure we're not going over our 10 minute mark
        start = datetime.utcnow()
        end = start + timedelta(minutes=self.__config_manager.get_int(OVERSUBSCRIBE_WINDOW_SIZE_MINUTES_KEY,
                                                                      DEFAULT_OVERSUBSCRIBE_WINDOW_SIZE_MINUTES))

        simple_cpu_usage_predictions = self.__get_simple_cpu_predictions()

        workload_count = 0
        underutilized_cpu_count = 0

        for workload in self.__workload_manager.get_workloads():
            log.info('workload:%s job_type:%s cpu:%d', workload.get_app_name(), workload.get_job_type(),
                     workload.get_thread_count())

            if not self.__is_long_enough(workload):
                continue

            simple_cpu_prediction = simple_cpu_usage_predictions.get(workload.get_id(), None)
            if simple_cpu_prediction is None:
                log.warning("No CPU prediction for workload: %s", workload.get_id())
                continue

            # Process prediction
            pred_usage = simple_cpu_prediction / workload.get_thread_count()
            threshold = self.__config_manager.get_float(TOTAL_THRESHOLD, DEFAULT_TOTAL_THRESHOLD)

            log.info("Testing oversubscribability of workload: {}, threshold: {}, prediction: {}".format(
                workload.get_id(), threshold, pred_usage))

            if pred_usage > threshold:
                log.info("Workload: %s is NOT oversubscribable: %s", workload.get_id(), pred_usage)
                continue

            log.info("Workload: %s is oversubscribable: %s", workload.get_id(), pred_usage)

            if workload.is_opportunistic():
                # only add the number of "real" threads (non-opportunistic)
                free = workload.get_thread_count() - workload.get_opportunistic_thread_count()
                if free <= 0:
                    continue
                underutilized_cpu_count += free
            else:
                underutilized_cpu_count += workload.get_thread_count()
            workload_count += 1

        free_cpu_count = underutilized_cpu_count
        if free_cpu_count > 0:
            self.__window_publisher.add_window(start, end, free_cpu_count)
            self.__window_end_time = end

        self.__success_count += 1
        self.handled_event(event,
                           'oversubscribed {} cpus from {} workloads, {} total cpus are oversubscribed'.format(
                               free_cpu_count, workload_count, underutilized_cpu_count))

    def __relevant(self, event):
        if not event[ACTION] == OVERSUBSCRIBE:
            self.ignored_event(event, 'not a {} event'.format(OVERSUBSCRIBE))
            return False

        return True

    def __get_workload_duration(self, workload, min_duration_sec) -> float:
        if workload.is_service():
            return min_duration_sec

        duration_percentile = self.__config_manager.get_float(OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE_KEY,
                                                              DEFAULT_OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE)
        duration = get_duration(workload, duration_percentile)
        return duration if duration is not None else -1

    def __is_long_enough(self, workload) -> bool:
        min_duration_sec = 60 * self.__config_manager.get_int(OVERSUBSCRIBE_WINDOW_SIZE_MINUTES_KEY,
                                                              DEFAULT_OVERSUBSCRIBE_WINDOW_SIZE_MINUTES)
        workload_duration_sec = self.__get_workload_duration(workload, min_duration_sec)
        if workload_duration_sec < min_duration_sec:
            log.info(
                "Workload: {} is too short. workload_duration_sec: {} < min_duration_sec: {}".format(
                    workload.get_id(), workload_duration_sec, min_duration_sec))
            return False

        log.info(
            "Workload: {} is long enough. workload_duration_sec: {} >= min_duration_sec: {}".format(
                workload.get_id(), workload_duration_sec, min_duration_sec))
        return True
