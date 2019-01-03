from titus_isolate import log
from titus_isolate.exit_handler import ExitHandler


class TestExitHandler(ExitHandler):
    def __init__(self):
        self.last_code = None

    def exit(self, code):
        log.info("Mock exiting with code: '{}'".format(code))
        self.last_code = code
