import logging
from abc import abstractmethod

from titus_isolate import log


class EventHandler:
    def __init__(self, log_level=logging.INFO):
        self.__log_level = log_level
        self.__ignored_event_count = 0
        self.__handled_event_count = 0

    def ignored_event(self, event, msg):
        log.debug("'{}' ignored event. msg: '{}'".format(self.__class__.__name__, msg))
        self.__ignored_event_count += 1

    def handling_event(self, event, msg):
        log.log(self.__log_level, "'{}' handling event.  msg: '{}'".format(self.__class__.__name__, msg))

    def handled_event(self, event, msg):
        log.log(self.__log_level, "'{}' handled event.  msg: '{}'".format(self.__class__.__name__, msg))
        self.__handled_event_count += 1

    def get_ignored_event_count(self):
        return self.__ignored_event_count

    def get_handled_event_count(self):
        return self.__handled_event_count

    @abstractmethod
    def handle(self, event):
        pass

