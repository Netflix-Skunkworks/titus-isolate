import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


class EventLogger:
    @staticmethod
    def handle(event):
        log.info("event: '{}'".format(event))
