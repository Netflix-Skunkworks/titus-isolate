from titus_isolate import log
from titus_isolate.metrics.event_log_manager import EventLogManager


class TestEventLogManager(EventLogManager):
    def __init__(self):
        self.payloads = []

    def report_event(self, payload: dict):
        log.info("Mock reporting event: {}".format(payload))
        self.payloads.append(payload)

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
