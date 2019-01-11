import json
from queue import Queue, Empty
from threading import Thread

from titus_isolate import log
from titus_isolate.cgroup.file_manager import FileManager
from titus_isolate.config.constants import WAIT_CGROUP_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC
from titus_isolate.docker.constants import ACTION, CREATE
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.utils import get_container_name
from titus_isolate.utils import get_config_manager

DEFAULT_EVENT_TIMEOUT_SECS = 60


class EventManager:
    def __init__(self, event_iterable, event_handlers, file_manager=FileManager(), event_timeout=DEFAULT_EVENT_TIMEOUT_SECS):
        self.__stopped = False
        self.__raw_q = Queue()
        self.__groomed_q = Queue()

        self.__events = event_iterable
        self.__event_handlers = event_handlers
        self.__event_logger = EventLogger()
        self.__event_timeout = event_timeout

        self.__file_manger = file_manager

        self.__success_event_count = 0
        self.__error_event_count = 0
        self.__processed_event_count = 0

        self.__processing_thread = Thread(target=self.__groom_events)
        self.__processing_thread.start()

        self.__processing_thread = Thread(target=self.__process_events)
        self.__processing_thread.start()

        self.__pulling_thread = Thread(target=self.__pull_events)
        self.__pulling_thread.start()

    def join(self):
        self.__pulling_thread.join()
        self.__processing_thread.join()

    def stop_processing_events(self):
        self.__stopped = True
        self.__events.close()
        self.join()

    def get_success_count(self):
        return self.__success_event_count

    def get_error_count(self):
        return self.__error_event_count

    def get_processed_count(self):
        return self.__processed_event_count

    def get_queue_depth(self):
        return self.__raw_q.qsize()

    def __pull_events(self):
        for event in self.__events:
            self.__raw_q.put(event)

    def __groom_events(self):
        while not self.__stopped:
            try:
                event = self.__raw_q.get(timeout=self.__event_timeout)
            except Empty:
                log.debug("Timed out waiting for event on queue.")
                continue

            event = event.decode("utf-8")
            event = json.loads(event)
            self.__event_logger.handle(event)

            Thread(target=self.__groom, args=[event]).start()

    def __groom(self, event):
        if not event[ACTION] == CREATE:
            self.__groomed_q.put_nowait(event)
            return

        try:
            name = get_container_name(event)
            log.info("Grooming create event for: '{}'".format(name))

            self.__file_manger.wait_for_files(name)
            log.info("Groomed create event for: '{}'".format(name))
            self.__groomed_q.put_nowait(event)
        except:
            self.__error_event_count += 1
            log.exception("Dropping CREATE event, because failed to wait for files for: '{}'".format(name))

    def __process_events(self):
        while not self.__stopped:
            try:
                event = self.__groomed_q.get(timeout=self.__event_timeout)
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

            self.__raw_q.task_done()
            self.__processed_event_count += 1
            log.debug("processed event count: {}".format(self.get_success_count()))
