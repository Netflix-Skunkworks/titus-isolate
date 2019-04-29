import copy

from titus_isolate.allocate.constants import CPU, CPU_USAGE, WORKLOADS, METADATA
from titus_isolate.allocate.utils import parse_cpu, parse_workloads, parse_cpu_usage
from titus_isolate.model.processor.cpu import Cpu


class AllocateRequest:

    def __init__(self, cpu: Cpu, workloads: dict, cpu_usage: dict, metadata: dict):
        """
        A rebalance request encapsulates all information needed to rebalance the assignment of threads to workloads.

        :param cpu: An object indicating the state of the CPU before workload assignment
        :param workloads: A map of all relevant workloads including the workload to be assigned
                          The keys are workload ids, the objects are Workload objects
        :param cpu_usage: A map of cpu usage per workload
        """
        self.__cpu = copy.deepcopy(cpu)
        self.__workloads = copy.deepcopy(workloads)
        self.__cpu_usage = copy.deepcopy(cpu_usage)
        self.__metadata = copy.deepcopy(metadata)

    def get_cpu(self):
        return self.__cpu

    def get_cpu_usage(self):
        return self.__cpu_usage

    def get_workloads(self):
        return self.__workloads

    def get_metadata(self):
        return self.__metadata

    def to_dict(self):
        return {
            CPU: self.get_cpu().to_dict(),
            CPU_USAGE: self.__get_serializable_usage(self.get_cpu_usage()),
            WORKLOADS: self.__get_serializable_workloads(list(self.get_workloads().values())),
            METADATA: self.get_metadata()
        }

    @staticmethod
    def __get_serializable_usage(cpu_usage: dict):
        serializable_usage = {}
        for w_id, usage in cpu_usage.items():
            serializable_usage[w_id] = [str(u) for u in usage]
        return serializable_usage

    @staticmethod
    def __get_serializable_workloads(workloads: list):
        serializable_workloads = {}
        for w in workloads:
            serializable_workloads[w.get_id()] = w.to_dict()

        return serializable_workloads


def deserialize_allocate_request(serialized_request: dict) -> AllocateRequest:
    cpu = parse_cpu(serialized_request[CPU])
    workloads = parse_workloads(serialized_request[WORKLOADS])
    cpu_usage = parse_cpu_usage(serialized_request[CPU_USAGE])
    metadata = serialized_request[METADATA]
    return AllocateRequest(cpu, workloads, cpu_usage, metadata)
