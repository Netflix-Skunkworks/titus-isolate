import logging
import os

log = logging.getLogger()
log.setLevel(logging.INFO)

LOG_FMT_STRING = '%(asctime)s,%(msecs)d %(levelname)s [%(filename)s:%(lineno)d] %(message)s'


if "DISTRIB_ID" in os.environ:
    from systemd.journal import JournaldLogHandler
    journald_handler = JournaldLogHandler()
    journald_handler.setFormatter(logging.Formatter(LOG_FMT_STRING))
    log.addHandler(journald_handler)
