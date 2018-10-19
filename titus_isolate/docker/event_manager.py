import json
from threading import Thread


class EventManager:
    def __init__(self, event_iterable, event_handlers):
        self.__events = event_iterable
        self.__event_handlers = event_handlers
        self.__processed_event_count = 0
        self.__processing_thread = Thread(target=self.__process_events)
        self.__processing_thread.start()

    def stop_processing_events(self):
        self.__events.close()
        self.__processing_thread.join()

    def get_processed_event_count(self):
        return self.__processed_event_count

    def __process_events(self):
        for event in self.__events:
            for event_handler in self.__event_handlers:
                event_handler.handle(json.loads(event))
            self.__processed_event_count += 1
