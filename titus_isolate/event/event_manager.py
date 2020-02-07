import json
import time
from queue import Queue, Empty
from threading import Thread, Lock

import schedule

from titus_isolate import log
from titus_isolate.config.constants import REBALANCE_FREQUENCY_KEY, DEFAULT_REBALANCE_FREQUENCY, \
    RECONCILE_FREQUENCY_KEY, DEFAULT_RECONCILE_FREQUENCY, \
    OVERSUBSCRIBE_FREQUENCY_KEY, DEFAULT_OVERSUBSCRIBE_FREQUENCY
from titus_isolate.event.constants import REBALANCE_EVENT, RECONCILE_EVENT, OVERSUBSCRIBE_EVENT, ACTION, HANDLED_ACTIONS
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.metrics.constants import QUEUE_DEPTH_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY, \
    ENQUEUED_COUNT_KEY, DEQUEUED_COUNT_KEY, QUEUE_LATENCY_KEY
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.utils import get_config_manager

DEFAULT_EVENT_TIMEOUT_SECS = 60
ENQUEUE_TIME_KEY = "enqueue_time"


class EventManager(MetricsReporter):

    def __init__(self, event_iterable, event_handlers, event_timeout=DEFAULT_EVENT_TIMEOUT_SECS):
        self.__reg = None
        self.__tags = None
        self.__stopped = False
        self.__q = Queue()

        self.__events = event_iterable
        self.__event_handlers = event_handlers
        self.__event_timeout = event_timeout

        self.__processed_count = 0

        self.__started = False
        self.__started_lock = Lock()

        self.__processing_thread = Thread(target=self.__process_events)
        self.__pulling_thread = Thread(target=self.__pull_events)

        config_manager = get_config_manager()

        rebalance_frequency = config_manager.get_float(REBALANCE_FREQUENCY_KEY, DEFAULT_REBALANCE_FREQUENCY)
        if rebalance_frequency > 0:
            schedule.every(rebalance_frequency).seconds.do(self.__rebalance)

        reconcile_frequency = config_manager.get_float(RECONCILE_FREQUENCY_KEY, DEFAULT_RECONCILE_FREQUENCY)
        if reconcile_frequency > 0:
            schedule.every(reconcile_frequency).seconds.do(self.__reconcile)

        oversubscribe_frequency = config_manager.get_float(OVERSUBSCRIBE_FREQUENCY_KEY,
                                                           DEFAULT_OVERSUBSCRIBE_FREQUENCY)
        if oversubscribe_frequency > 0:
            schedule.every(oversubscribe_frequency).seconds.do(self.__oversubscribe)

    def join(self):
        self.__pulling_thread.join()
        self.__processing_thread.join()

    def stop_processing_events(self):
        self.__stopped = True
        self.__events.close()
        self.join()

    def start_processing_events(self):
        with self.__started_lock:
            if self.__started:
                return

            self.__processing_thread.start()
            self.__pulling_thread.start()
            self.__started = True

    def get_queue_depth(self):
        return self.__q.qsize()

    def get_processed_count(self):
        return self.__processed_count

    def __rebalance(self):
        self.__put_event(REBALANCE_EVENT)

    def __reconcile(self):
        self.__put_event(RECONCILE_EVENT)

    def __oversubscribe(self):
        self.__put_event(OVERSUBSCRIBE_EVENT)

    def __pull_events(self):
        for event in self.__events:
            self.__put_event(event)

    def __put_event(self, event):
        event = json.loads(event.decode("utf-8"))
        if event[ACTION] in HANDLED_ACTIONS:
            log.info("Enqueuing event: {}, queue depth: {}".format(event[ACTION], self.get_queue_depth()))
            event[ENQUEUE_TIME_KEY] = time.time()
            self.__q.put(event)
            if self.__reg is not None:
                self.__reg.counter(ENQUEUED_COUNT_KEY, self.__tags).increment()
                self.__reg.counter(self.__get_enqueued_metric_name(event), self.__tags).increment()

    def __process_events(self):
        while not self.__stopped:
            try:
                event = self.__q.get(timeout=self.__event_timeout)
                dequeue_time = time.time()
                log.info("Dequeued event: {}, queue depth: {}".format(event[ACTION], self.get_queue_depth()))
                if self.__reg is not None:
                    self.__reg.counter(DEQUEUED_COUNT_KEY, self.__tags).increment()
                    self.__reg.counter(self.__get_dequeued_metric_name(event), self.__tags).increment()
                    self.__reg.distribution_summary(QUEUE_LATENCY_KEY, self.__tags).record(dequeue_time - event[ENQUEUE_TIME_KEY])
            except Empty:
                log.debug("Timed out waiting for event on queue.")
                continue

            for event_handler in self.__event_handlers:
                try:
                    log.info("{} handling event: {}".format(type(event_handler).__name__, event[ACTION]))
                    event_handler.handle(event)
                    self.__report_succeeded_event(event_handler)
                except:
                    log.exception("Event handler: '{}' failed to handle event: '{}'".format(
                        type(event_handler).__name__, event))
                    self.__report_failed_event(event_handler)

            self.__q.task_done()
            self.__reg.counter(EVENT_PROCESSED_KEY, self.__tags).increment()
            self.__reg.gauge(QUEUE_DEPTH_KEY, self.__tags).set(self.get_queue_depth())
            self.__processed_count += 1

    def __report_succeeded_event(self, event_handler: EventHandler):
        if self.__reg is not None:
            self.__reg.counter(self.__get_event_succeeded_metric_name(event_handler), self.__tags).increment()
            self.__reg.counter(EVENT_SUCCEEDED_KEY, self.__tags).increment()

    def __report_failed_event(self, event_handler: EventHandler):
        if self.__reg is not None:
            self.__reg.counter(self.__get_event_failed_metric_name(event_handler), self.__tags).increment()
            self.__reg.counter(EVENT_FAILED_KEY, self.__tags).increment()

    @staticmethod
    def __get_event_succeeded_metric_name(event_handler: EventHandler) -> str:
        return "titus-isolate.{}.eventSucceeded".format(type(event_handler).__name__)

    @staticmethod
    def __get_event_failed_metric_name(event_handler: EventHandler) -> str:
        return "titus-isolate.{}.eventFailed".format(type(event_handler).__name__)

    @staticmethod
    def __get_enqueued_metric_name(event) -> str:
        return "titus-isolate.{}.eventEnqueued".format(event[ACTION])

    @staticmethod
    def __get_dequeued_metric_name(event) -> str:
        return "titus-isolate.{}.eventDequeued".format(event[ACTION])

    def set_registry(self, registry, tags):
        self.__reg = registry
        self.__tags = tags

    def report_metrics(self, tags):
        pass
