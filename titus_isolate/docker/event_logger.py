from titus_isolate.utils import get_logger

log = get_logger()


class EventLogger:
    @staticmethod
    def handle(event):
        log.info("event: '{}'".format(event))
