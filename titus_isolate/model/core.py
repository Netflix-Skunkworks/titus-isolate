class Core:
    def __init__(self, threads):
        if len(threads) < 1:
            raise ValueError("A CPU core must have at least 1 thread")

        self.__threads = threads

    def get_threads(self):
        return self.__threads

    def get_empty_threads(self):
        return [t for t in self.get_threads() if not t.is_claimed()]
