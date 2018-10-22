import logging

log = logging.getLogger()


class EventLogger:
    @staticmethod
    def handle(event):
        log.info("event: '{}'".format(event))
