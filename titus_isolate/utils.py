import logging
import time
from threading import Thread

import schedule

from titus_isolate import log

SCHEDULING_SLEEP_INTERVAL = 1.0


def get_logger(level=logging.INFO):
    log.setLevel(level)
    return log


def start_periodic_scheduling():
    worker_thread = Thread(target=__schedule_loop)
    worker_thread.daemon = True
    worker_thread.start()


def __schedule_loop():
    while True:
        schedule.run_pending()

        sleep_time = SCHEDULING_SLEEP_INTERVAL
        if schedule.next_run() is not None:
            sleep_time = schedule.idle_seconds()

        time.sleep(sleep_time)
