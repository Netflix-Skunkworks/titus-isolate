from abc import abstractmethod


class ExitHandler:

    @abstractmethod
    def exit(self, code):
        pass
