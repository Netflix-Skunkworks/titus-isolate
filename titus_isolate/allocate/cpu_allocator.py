import abc

from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.metrics.metrics_reporter import MetricsReporter


class CpuAllocator(abc.ABC, MetricsReporter):

    @abc.abstractmethod
    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        """
        Implementations of this method should claim threads for a workload on a given CPU.
        """
        pass

    @abc.abstractmethod
    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        """
        Implementations of this method should free threads claimed by a workload on a given CPU.
        """
        pass

    @abc.abstractmethod
    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        """
        This method will be called periodically to provide an opportunity to move already running
        workloads according to whatever policy the allocator deems appropriate.  Examples policies
        may choose to oversubscribe resources or improve isolation.
        """
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
