import copy
from typing import Dict, List

from titus_isolate.allocate.constants import CPU, CPU_ARRAY, CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, \
    DISK_USAGE, WORKLOADS, RESOURCE_USAGE, METADATA
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload_interface import Workload
from titus_isolate.utils import get_workload_monitor_manager


class AllocateRequest:

    def __init__(self,
                 cpu: Cpu,
                 workloads: Dict[str, Workload],
                 metadata: dict):
        self.__cpu = copy.deepcopy(cpu)
        self.__workloads = copy.deepcopy(workloads)
        self.__metadata = copy.deepcopy(metadata)

        # We need to keep populating this data into the titus-isolate event stream
        # TODO: Stop populating this usage data when consumers of this usage data complete deprecation
        wmm = get_workload_monitor_manager()
        resource_usage = wmm.get_resource_usage(workloads.keys())
        self.__resource_usage = resource_usage
        self.__cpu_usage = self.__get_optional_default(resource_usage.get_cpu_usage, {})
        self.__mem_usage = self.__get_optional_default(resource_usage.get_mem_usage, {})
        self.__net_recv_usage = self.__get_optional_default(resource_usage.get_net_recv_usage, {})
        self.__net_trans_usage = self.__get_optional_default(resource_usage.get_net_trans_usage, {})
        self.__disk_usage = self.__get_optional_default(resource_usage.get_disk_usage, {})

    def get_cpu(self):
        return self.__cpu

    def get_workloads(self) -> Dict[str, Workload]:
        return self.__workloads

    def get_metadata(self):
        return self.__metadata

    def to_dict(self) -> dict:
        return {
            CPU: self.get_cpu().to_dict(),
            CPU_ARRAY: self.get_cpu().to_array(),
            CPU_USAGE: self.__get_serializable_usage(self.__cpu_usage),
            MEM_USAGE: self.__get_serializable_usage(self.__mem_usage),
            NET_RECV_USAGE: self.__get_serializable_usage(self.__net_recv_usage),
            NET_TRANS_USAGE: self.__get_serializable_usage(self.__net_trans_usage),
            DISK_USAGE: self.__get_serializable_usage(self.__disk_usage),
            WORKLOADS: self.__get_serializable_workloads(list(self.get_workloads().values())),
            RESOURCE_USAGE: self.__resource_usage.serialize(),
            METADATA: self.get_metadata()
        }

    @staticmethod
    def __get_serializable_workloads(workloads: List[Workload]):
        serializable_workloads = {}
        for w in workloads:
            serializable_workloads[w.get_task_id()] = w.to_dict()

        return serializable_workloads

    @staticmethod
    def __get_serializable_usage(cpu_usage: dict):
        serializable_usage = {}
        for w_id, usage in cpu_usage.items():
            serializable_usage[w_id] = [str(u) for u in usage]
        return serializable_usage

    @staticmethod
    def __get_optional_default(func, default):
        opt = func()
        if opt is None:
            return default
        return opt
