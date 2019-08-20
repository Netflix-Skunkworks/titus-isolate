import abc
from typing import List, Tuple


class UsageSnapshot(abc.ABC):

    @abc.abstractmethod
    def get_column(self) -> Tuple[float, List[float]]:
        pass
