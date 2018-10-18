from titus_isolate.model.processor import utils


class Core:
    def __init__(self, identifier, threads):
        if len(threads) < 1:
            raise ValueError("A CPU core must have at least 1 thread")

        self.__identifier = identifier
        self.__threads = threads

    def get_id(self):
        return self.__identifier

    def get_threads(self):
        return self.__threads

    def get_empty_threads(self):
        return utils.get_empty_threads(self.get_threads())
