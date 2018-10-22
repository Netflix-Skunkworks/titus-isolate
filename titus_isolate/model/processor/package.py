from functools import reduce

from titus_isolate.model.processor import utils


class Package:
    def __init__(self, identifier, cores):
        if len(cores) < 1:
            raise ValueError("A CPU package must have at least 1 core.")

        self.__identifier = identifier
        self.__cores = cores

    def get_id(self):
        return self.__identifier

    def get_cores(self):
        return self.__cores

    def get_threads(self):
        return reduce(list.__add__, [core.get_threads() for core in self.get_cores()])

    def get_empty_threads(self):
        return utils.get_empty_threads(self.get_threads())
