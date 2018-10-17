from titus_isolate.model.processor.utils import get_empty_threads


class Core:
    def __init__(self, threads):
        if len(threads) < 1:
            raise ValueError("A CPU core must have at least 1 thread")

        self.__threads = threads

    def get_threads(self):
        return self.__threads

    def get_empty_threads(self):
        return get_empty_threads(self.get_threads())
