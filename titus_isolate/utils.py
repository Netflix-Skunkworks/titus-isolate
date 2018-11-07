import logging

from titus_isolate import log


def get_logger(level=logging.INFO):
    log.setLevel(level)
    return log
