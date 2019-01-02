from abc import abstractmethod


class PropertyProvider:

    @abstractmethod
    def get(self, key):
        pass
