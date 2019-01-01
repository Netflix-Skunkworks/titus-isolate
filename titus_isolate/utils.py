import logging
import time
from threading import Thread, Lock

import schedule

from titus_isolate import log

SCHEDULING_SLEEP_INTERVAL = 1.0

scheduling_lock = Lock()
scheduling_started = False


def get_logger(level=logging.INFO):
    log.setLevel(level)
    return log


def start_periodic_scheduling():
    global scheduling_started

    with scheduling_lock:
        if scheduling_started:
            return

        worker_thread = Thread(target=__schedule_loop)
        worker_thread.daemon = True
        worker_thread.start()
        scheduling_started = True


def __schedule_loop():
    while True:
        log.debug("Running pending scheduled tasks.")
        schedule.run_pending()

        sleep_time = SCHEDULING_SLEEP_INTERVAL
        if schedule.next_run() is not None:
            sleep_time = schedule.idle_seconds()

        if sleep_time < 0:
            sleep_time = SCHEDULING_SLEEP_INTERVAL

        log.debug("Scheduling thread sleeping for: '{}' seconds".format(sleep_time))
        time.sleep(sleep_time)
