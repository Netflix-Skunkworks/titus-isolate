from functools import reduce

from titus_isolate.model.processor.utils import get_empty_threads


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

    def get_emptiest_core(self):
        emptiest_core = self.get_cores()[0]
        curr_empty_thread_count = len(emptiest_core.get_empty_threads())

        for core in self.get_cores()[1:]:
            new_empty_thread_count = len(core.get_empty_threads())
            if new_empty_thread_count > curr_empty_thread_count:
                emptiest_core = core
                curr_empty_thread_count = new_empty_thread_count

        return emptiest_core

    def get_threads(self):
        return reduce(list.__add__, [core.get_threads() for core in self.get_cores()])

    def get_empty_threads(self):
        return get_empty_threads(self.get_threads())
