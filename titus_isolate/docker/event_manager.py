import json
from queue import Queue, Empty
from threading import Thread

from titus_isolate.utils import get_logger

log = get_logger()

DEFAULT_EVENT_TIMEOUT_SECS = 60


class EventManager:
    def __init__(self, event_iterable, event_handlers, event_timeout=DEFAULT_EVENT_TIMEOUT_SECS):
        self.__stopped = False
        self.__q = Queue()

        self.__events = event_iterable
        self.__event_handlers = event_handlers
        self.__event_timeout = event_timeout

        self.__processed_event_count = 0
        self.__handle_event_count = 0
        self.__error_event_count = 0

        self.__processing_thread = Thread(target=self.__process_events)
        self.__processing_thread.start()

        self.__pulling_thread = Thread(target=self.__pull_events)
        self.__pulling_thread.start()

    def stop_processing_events(self):
        self.__stopped = True
        self.__events.close()
        self.__pulling_thread.join()
        self.__processing_thread.join()

    def get_processed_event_count(self):
        return self.__processed_event_count

    def get_error_event_count(self):
        return self.__error_event_count

    def get_queue_depth(self):
        return self.__q.qsize()

    def __pull_events(self):
        for event in self.__events:
            self.__q.put(event)

    def __process_events(self):
        while not self.__stopped:
            try:
                event = self.__q.get(timeout=self.__event_timeout)
            except Empty:
                log.debug("Timed out waiting for event on queue.")
                continue

            event = event.decode("utf-8")
            for event_handler in self.__event_handlers:
                try:
                    event_handler.handle(json.loads(event))
                except:
                    log.exception("Event handler: '{}' failed to handle event: '{}'".format(
                        type(event_handler).__name__, event))
                    self.__error_event_count += 1

            self.__processed_event_count += 1
            self.__q.task_done()
            log.debug("processed event count: {}".format(self.get_processed_event_count()))
