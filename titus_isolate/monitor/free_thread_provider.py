from abc import abstractmethod

from titus_isolate.model.processor.cpu import Cpu


class FreeThreadProvider:

    @abstractmethod
    def get_free_threads(self, cpu: Cpu) -> list:
        pass
