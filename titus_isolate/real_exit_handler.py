import os
import signal
import time

from titus_isolate import log
from titus_isolate.exit_handler import ExitHandler


class RealExitHandler(ExitHandler):

    def __init__(self):
        signal.signal(signal.SIGINT, self.__sig_exit)
        signal.signal(signal.SIGTERM, self.__sig_exit)

    def __sig_exit(self, signum, frame):
        log.info("Exiting due to signal: {} and frame: {}".format(signum, frame))
        self.exit(signum)

    def exit(self, code):
        # Sleep for 1 second so log messages get flushed.
        time.sleep(0.1)
        os._exit(code)
