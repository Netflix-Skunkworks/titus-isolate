from typing import List

from titus_isolate.model.processor import utils
from titus_isolate.model.processor.thread import Thread


class Core:
    def __init__(self, identifier, threads):
        if len(threads) < 1:
            raise ValueError("A CPU core must have at least 1 thread")

        self.__identifier = identifier
        self.__threads = threads

    def get_id(self):
        return self.__identifier

    def get_threads(self) -> List[Thread]:
        return self.__threads

    def get_empty_threads(self):
        return utils.get_empty_threads(self.get_threads())

    def __eq__(self, other):
        if isinstance(other, Core):
            return self.get_id() == other.get_id() and \
                   set(self.get_threads()) == set(other.get_threads())
        return NotImplemented

    def __hash__(self):
        return hash(tuple([self.get_id(), frozenset(self.get_threads())]))
