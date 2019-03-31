import logging
import os

from titus_isolate.config.constants import LOG_FMT_STRING

log = logging.getLogger()
log.setLevel(logging.INFO)


if "DISTRIB_ID" in os.environ:
    from systemd.journal import JournaldLogHandler
    journald_handler = JournaldLogHandler()
    journald_handler.setFormatter(logging.Formatter(LOG_FMT_STRING))
    log.addHandler(journald_handler)
