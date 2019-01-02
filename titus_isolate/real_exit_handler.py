import os

from titus_isolate.exit_handler import ExitHandler


class RealExitHandler(ExitHandler):

    def exit(self, code):
        os._exit(code)
