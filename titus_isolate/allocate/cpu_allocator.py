import abc

from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.metrics.metrics_reporter import MetricsReporter


class CpuAllocator(abc.ABC, MetricsReporter):

    @abc.abstractmethod
    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        """
        This method returns the name of the allocator.  It is notably used to tag metrics and event logs.
        :return:
        """
        pass

    def str(self):
        return self.__class__.__name__

