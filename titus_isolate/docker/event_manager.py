import json
from queue import Queue, Empty
from threading import Thread, Lock

from titus_isolate import log
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.metrics.constants import QUEUE_DEPTH_KEY, EVENT_SUCCEEDED_KEY, EVENT_FAILED_KEY, EVENT_PROCESSED_KEY
from titus_isolate.metrics.metrics_reporter import MetricsReporter

DEFAULT_EVENT_TIMEOUT_SECS = 60


class EventManager(MetricsReporter):

    def __init__(self, event_iterable, event_handlers, event_timeout=DEFAULT_EVENT_TIMEOUT_SECS):
        self.__reg = None
        self.__stopped = False
        self.__q = Queue()

        self.__events = event_iterable
        self.__event_handlers = event_handlers
        self.__event_logger = EventLogger()
        self.__event_timeout = event_timeout

        self.__success_event_count = 0
        self.__error_event_count = 0
        self.__processed_event_count = 0

        self.__started = False
        self.__started_lock = Lock()

        self.__processing_thread = Thread(target=self.__process_events)
        self.__pulling_thread = Thread(target=self.__pull_events)

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

    def get_success_count(self):
        return self.__success_event_count

    def get_error_count(self):
        return self.__error_event_count

    def get_processed_count(self):
        return self.__processed_event_count

    def get_queue_depth(self):
        return self.__q.qsize()

    def __pull_events(self):
        for event in self.__events:
            self.__q.put(event)

    def __process_events(self):
        while not self.__stopped:
            try:
                event = self.__q.get(timeout=self.__event_timeout)
                event = json.loads(event.decode("utf-8"))
            except Empty:
                log.debug("Timed out waiting for event on queue.")
                continue

            for event_handler in self.__event_handlers:
                try:
                    event_handler.handle(event)
                    self.__success_event_count += 1
                except:
                    log.exception("Event handler: '{}' failed to handle event: '{}'".format(
                        type(event_handler).__name__, event))
                    self.__error_event_count += 1

            self.__q.task_done()
            self.__processed_event_count += 1
            log.debug("processed event count: {}".format(self.get_success_count()))

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(QUEUE_DEPTH_KEY, tags).set(self.get_queue_depth())
        self.__reg.gauge(EVENT_SUCCEEDED_KEY, tags).set(self.get_success_count())
        self.__reg.gauge(EVENT_FAILED_KEY, tags).set(self.get_error_count())
        self.__reg.gauge(EVENT_PROCESSED_KEY, tags).set(self.get_processed_count())

