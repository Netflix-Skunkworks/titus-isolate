import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


class EventHandler:
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager
        self.__ignored_event_count = 0
        self.__handled_event_count = 0

    def ignored_event(self, event, msg):
        log.debug("Ignored event. msg: '{}', event: '{}', ".format(msg, event))
        self.__ignored_event_count += 1

    def handled_event(self, event, msg):
        log.info("Handled event.  msg: '{}', event: '{}'".format(msg, event))
        self.__handled_event_count += 1

    def get_ignored_event_count(self):
        return self.__ignored_event_count

    def get_handled_event_count(self):
        return self.__handled_event_count

