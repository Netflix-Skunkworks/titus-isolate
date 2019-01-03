from titus_isolate import log


class EventLogger:
    @staticmethod
    def handle(event):
        log.info("event: '{}'".format(event))
