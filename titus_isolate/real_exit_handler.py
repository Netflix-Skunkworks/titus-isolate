import os
import time

from titus_isolate.exit_handler import ExitHandler


class RealExitHandler(ExitHandler):

    def exit(self, code):
        # Sleep for 1 second so log messages get flushed.
        time.sleep(1)
        os._exit(code)
