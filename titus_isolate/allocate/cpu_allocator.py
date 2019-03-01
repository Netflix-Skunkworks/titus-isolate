import abc

from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu


class CpuAllocator(abc.ABC, MetricsReporter):

    @abc.abstractmethod
    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        """
        Implementations of this method should claim threads for a workload on a given CPU.

        :param cpu: An object indicating the state of the CPU before workload assignment
        :param workload_id: The id of the workload being assigned.
        :param workloads: A map of all relevant workloads including the workload to be assigned.
        The keys are workload ids, the objects are Workload objects.
        """
        pass

    @abc.abstractmethod
    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        """
        Implementations of this method should free threads claimed by a workload on a given CPU.

        :param cpu: An object indicating the state of the CPU before freeing threads
        :param workload_id: The id of the workload being removed.
        :param workloads: A map of all relevant workloads including the workload to be removed.
        The keys are workload ids, the values are Workload objects.
        """
        pass

    @abc.abstractmethod
    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        """
        This method will be called periodically to provide an opportunity to move already running
        workloads according to whatever policy the allocator deems appropriate.  Examples policies
        may choose to oversubscribe resources or improve isolation.

        :param cpu: An object indicating the state of the CPU before freeing threads
        :param workloads: A map of all relevant workloads including the workload to be removed.
        The keys are workload ids, the values are Workload objects.
        """
        pass

    def str(self):
        return self.__class__.__name__
