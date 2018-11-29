from titus_isolate.utils import get_logger

log = get_logger()


class EventHandler:
    def __init__(self, workload_manager):
        self.workload_manager = workload_manager
        self.__ignored_event_count = 0
        self.__handled_event_count = 0

    def ignored_event(self, event, msg):
        log.debug("'{}' ignored event. msg: '{}', event: '{}', ".format(self.__class__.__name__, msg, event))
        self.__ignored_event_count += 1

    def handling_event(self, event, msg):
        log.info("'{}' handling event.  msg: '{}', event: '{}'".format(self.__class__.__name__, msg, event))

    def handled_event(self, event, msg):
        log.info("'{}' handled event.  msg: '{}', event: '{}'".format(self.__class__.__name__, msg, event))
        self.__handled_event_count += 1

    def get_ignored_event_count(self):
        return self.__ignored_event_count

    def get_handled_event_count(self):
        return self.__handled_event_count

