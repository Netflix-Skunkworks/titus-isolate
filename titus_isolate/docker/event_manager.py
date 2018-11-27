import json
from threading import Thread

from titus_isolate.utils import get_logger

log = get_logger()


class EventManager:
    def __init__(self, event_iterable, event_handlers):
        self.__events = event_iterable
        self.__event_handlers = event_handlers

        self.__processed_event_count = 0
        self.__handle_event_count = 0
        self.__error_event_count = 0

        self.__processing_thread = Thread(target=self.__process_events)
        self.__processing_thread.start()

    def stop_processing_events(self):
        self.__events.close()
        self.__processing_thread.join()

    def get_processed_event_count(self):
        return self.__processed_event_count

    def get_error_event_count(self):
        return self.__error_event_count

    def __process_events(self):
        for event in self.__events:
            event = event.decode("utf-8")
            for event_handler in self.__event_handlers:
                try:
                    event_handler.handle(json.loads(event))
                except:
                    log.exception("Event handler: '{}' failed to handle event: '{}'".format(
                        type(event_handler).__name__, event))
                    self.__error_event_count += 1

            self.__processed_event_count += 1
            log.debug("processed event count: {}".format(self.get_processed_event_count()))
