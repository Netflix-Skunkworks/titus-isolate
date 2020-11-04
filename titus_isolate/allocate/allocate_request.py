import copy
from typing import Dict

from titus_isolate.allocate.constants import CPU, CPU_USAGE, WORKLOADS, METADATA, CPU_ARRAY, MEM_USAGE, NET_RECV_USAGE, \
    NET_TRANS_USAGE, DISK_USAGE, RESOURCE_USAGE
from titus_isolate.allocate.utils import parse_cpu, parse_legacy_workloads, parse_usage
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.resource_usage import GlobalResourceUsage, deserialize_global_resource_usage


class AllocateRequest:

    def __init__(self, cpu: Cpu, workloads: dict, metadata: dict):
        """
        A rebalance request encapsulates all information needed to rebalance the assignment of threads to workloads.
        """
        self.__cpu = copy.deepcopy(cpu)
        self.__workloads = copy.deepcopy(workloads)
        self.__metadata = copy.deepcopy(metadata)

    def get_cpu(self):
        return self.__cpu

    def get_workloads(self) -> Dict[str, Workload]:
        return self.__workloads

    def get_metadata(self):
        return self.__metadata

    def to_dict(self):
        return {
            CPU: self.get_cpu().to_dict(),
            CPU_ARRAY: self.get_cpu().to_array(),
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
    workloads = parse_legacy_workloads(serialized_request[WORKLOADS])
    metadata = serialized_request[METADATA]
    return AllocateRequest( cpu=cpu, workloads=workloads, metadata=metadata)
