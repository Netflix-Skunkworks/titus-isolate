from abc import abstractmethod

from titus_isolate.metrics.event_log_manager import EventLogManager


class EventReporter:

    @abstractmethod
    def set_event_log_manager(self, event_log_manager: EventLogManager):
        pass
