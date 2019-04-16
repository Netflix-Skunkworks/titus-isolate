import abc

from titus_isolate import log
from titus_isolate.metrics.event_log import get_cpu_event
from titus_isolate.metrics.event_log_manager import EventLogManager
from titus_isolate.metrics.event_reporter import EventReporter
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu


class CpuAllocator(abc.ABC, MetricsReporter, EventReporter):

    @abc.abstractmethod
    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        """
        Implementations of this method should claim threads for a workload on a given CPU.

        :param cpu: An object indicating the state of the CPU before workload assignment
        :param workload_id: The id of the workload being assigned.
        :param workloads: A map of all relevant workloads including the workload to be assigned.
        :param cpu_usage: A map of cpu usage per workload per thread
        :param instance_id: The instance (host) on which workloads are being isolated.
        The keys are workload ids, the objects are Workload objects.
        """
        pass

    @abc.abstractmethod
    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        """
        Implementations of this method should free threads claimed by a workload on a given CPU.

        :param cpu: An object indicating the state of the CPU before freeing threads
        :param workload_id: The id of the workload being removed.
        :param workloads: A map of all relevant workloads including the workload to be removed.
        :param cpu_usage: A map of cpu usage per workload per thread
        :param instance_id: The instance (host) on which workloads are being isolated.
        The keys are workload ids, the values are Workload objects.
        """
        pass

    @abc.abstractmethod
    def rebalance(self, cpu: Cpu, workloads: dict, cpu_usage: dict, instance_id: str) -> Cpu:
        """
        This method will be called periodically to provide an opportunity to move already running
        workloads according to whatever policy the allocator deems appropriate.  Examples policies
        may choose to oversubscribe resources or improve isolation.

        :param cpu: An object indicating the state of the CPU before freeing threads
        :param workloads: A map of all relevant workloads including the workload to be removed.
        :param cpu_usage: A map of cpu usage per workload per thread
        :param instance_id: The instance (host) on which workloads are being isolated.
        The keys are workload ids, the values are Workload objects.
        """
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        """
        This method returns the name of the allocator.  It is notably used to tag metrics.
        :return:
        """
        pass

    @staticmethod
    def report_cpu_event(
            event_log_manager: EventLogManager,
            cpu: Cpu,
            workloads: list,
            cpu_usage: dict,
            instance_id: str,
            extra_meta: dict = None):

        if event_log_manager is None:
            log.warning("Event log manager is not set.")
            return

        evt = get_cpu_event(cpu, workloads, cpu_usage, instance_id)
        if extra_meta is not None:
            evt['payload']['alloc_extra_meta'] = extra_meta
        event_log_manager.report_event(evt)

    def str(self):
        return self.__class__.__name__
