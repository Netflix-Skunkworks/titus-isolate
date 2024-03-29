import itertools
import json
import time
from queue import Queue, Empty
from threading import Thread, Lock
from datetime import datetime
from random import randrange
from typing import List

import schedule

from titus_isolate import log
from titus_isolate.config.constants import REBALANCE_FREQUENCY_KEY, DEFAULT_REBALANCE_FREQUENCY, \
    RECONCILE_FREQUENCY_KEY, DEFAULT_RECONCILE_FREQUENCY, \
    PREDICT_RESOURCE_USAGE_FREQUENCY_KEY, \
    DEFAULT_PREDICT_RESOURCE_USAGE_FREQUENCY
from titus_isolate.event.constants import REBALANCE_EVENT, RECONCILE_EVENT, ACTION, \
    HANDLED_ACTIONS, PREDICT_USAGE_EVENT, CONTAINER_EVENTS, INTERNAL_EVENTS, CONTAINER_BATCH, STARTS, DIES, \
    START, DIE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import get_task_id, get_container_name
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
        self.last_successful_event_epoch_s = 0

        config_manager = get_config_manager()

        # Every instance of titus-isolate getting restarted at once produces scheduling spikes of events like
        # rebalance
        random_jitter = randrange(10)  # 0-9 inclusive

        rebalance_frequency = config_manager.get_float(REBALANCE_FREQUENCY_KEY, DEFAULT_REBALANCE_FREQUENCY)
        if rebalance_frequency > 0:
            schedule.every(rebalance_frequency + random_jitter).seconds.do(self.__rebalance)

        reconcile_frequency = config_manager.get_float(RECONCILE_FREQUENCY_KEY, DEFAULT_RECONCILE_FREQUENCY)
        if reconcile_frequency > 0:
            schedule.every(reconcile_frequency + random_jitter).seconds.do(self.__reconcile)

        predict_resource_usage_frequency = config_manager.get_float(PREDICT_RESOURCE_USAGE_FREQUENCY_KEY,
                                                                    DEFAULT_PREDICT_RESOURCE_USAGE_FREQUENCY)

        if predict_resource_usage_frequency > 0:
            schedule.every(predict_resource_usage_frequency + random_jitter).seconds.do(self.__predict_usage)

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

    def __predict_usage(self):
        self.__put_event(PREDICT_USAGE_EVENT)

    def __pull_events(self):
        for event in self.__events:
            self.__put_event(event)

    def __put_event(self, event):
        event = json.loads(event.decode("utf-8"))
        if self.__should_handle(event):
            log.info("Enqueuing event: {}, queue depth: {}".format(event[ACTION], self.get_queue_depth()))
            event[ENQUEUE_TIME_KEY] = time.time()
            self.__q.put(event)
            if self.__reg is not None:
                self.__reg.counter(ENQUEUED_COUNT_KEY, self.__tags).increment()
                self.__reg.counter(self.__get_enqueued_metric_name(event), self.__tags).increment()

    @staticmethod
    def __should_handle(event):
        if event[ACTION] not in HANDLED_ACTIONS:
            return False

        if event[ACTION] in CONTAINER_EVENTS:
            # If the start or die event doesn't have a Titus Task ID tag, then it's none of our business.
            if get_task_id(event) == '':
                log.info("Ignoring event: %s, for container: %s", event[ACTION], get_container_name(event))
                return False

        return True

    @staticmethod
    def __get_container_events(events: List) -> List:
        return [event for event in events if event[ACTION] in CONTAINER_EVENTS]

    @staticmethod
    def __get_internal_events(events: List) -> List:
        return [event for event in events if event[ACTION] in INTERNAL_EVENTS]

    def __dequeue_event(self):
        try:
            event = self.__q.get(timeout=self.__event_timeout)
            dequeue_time = time.time()
            log.info("Dequeued event: {}, queue depth: {}".format(event[ACTION], self.get_queue_depth()))
            if self.__reg is not None:
                self.__reg.counter(DEQUEUED_COUNT_KEY, self.__tags).increment()
                self.__reg.counter(self.__get_dequeued_metric_name(event), self.__tags).increment()
                self.__reg.distribution_summary(QUEUE_LATENCY_KEY, self.__tags).record(
                    dequeue_time - event[ENQUEUE_TIME_KEY])
            return event
        except Empty:
            log.debug("Timed out waiting for event on queue.")
            return None

    def __get_batch(self) -> List:
        event = self.__dequeue_event()
        if event is None:
            return []

        events = [event]

        for _ in itertools.repeat(None, self.__q.qsize()):
            event = self.__dequeue_event()
            if event is None:
                break
            else:
                events.append(event)

        return events

    @staticmethod
    def __get_container_batch_event(container_events: List):
        batch_event = {
            ACTION: CONTAINER_BATCH,
            STARTS: [],
            DIES: [],
        }

        for event in container_events:
            if event[ACTION] == START:
                batch_event[STARTS].append(event)
            if event[ACTION] == DIE:
                batch_event[DIES].append(event)

        return batch_event

    def __process_events(self):
        while not self.__stopped:
            batch = self.__get_batch()
            if len(batch) == 0:
                log.info("Got empty batch")
                continue

            internal_events = self.__get_internal_events(batch)
            container_events = self.__get_container_events(batch)

            events = []
            if len(container_events) > 0:
                events.append(self.__get_container_batch_event(container_events))
            events = events + internal_events

            for event in events:
                for event_handler in self.__event_handlers:
                    try:
                        log.info("{} handling event: {}".format(type(event_handler).__name__, event[ACTION]))
                        event_handler.handle(event)
                        self.__report_succeeded_event(event_handler)
                    except Exception:
                        log.exception("Event handler: '{}' failed to handle event: '{}'".format(
                            type(event_handler).__name__, event))
                        self.__report_failed_event(event_handler)

            for _ in itertools.repeat(None, len(internal_events) + len(container_events)):
                self.__reg.counter(EVENT_PROCESSED_KEY, self.__tags).increment()
                self.__processed_count += 1
                self.__q.task_done()

            self.__reg.gauge(QUEUE_DEPTH_KEY, self.__tags).set(self.get_queue_depth())

    def __report_succeeded_event(self, event_handler: EventHandler):
        if self.__reg is not None:
            self.__reg.counter(self.__get_event_succeeded_metric_name(event_handler), self.__tags).increment()
            self.__reg.counter(EVENT_SUCCEEDED_KEY, self.__tags).increment()
            self.last_successful_event_epoch_s = datetime.utcnow().timestamp()

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
