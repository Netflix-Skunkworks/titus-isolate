import logging
import os

LOG_FMT_STRING = '%(asctime)s,%(msecs)d %(levelname)s [%(filename)s:%(lineno)d] %(message)s'


def get_logger(level=logging.INFO):
    log = logging.getLogger()
    log.setLevel(level)

    if "DISTRIB_ID" in os.environ:
        from systemd.journal import JournaldLogHandler
        journald_handler = JournaldLogHandler()
        journald_handler.setFormatter(logging.Formatter(LOG_FMT_STRING))
        log.addHandler(journald_handler)

    return log
