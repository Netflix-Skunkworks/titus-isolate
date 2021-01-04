from collections import deque
from typing import List, Dict, Set, Optional

from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE, \
    RESOURCE_USAGE_NAMES


class ResourceUsage:

    def __init__(self, workload_id: str, resource_name: str, start_time_epoch_sec: float, interval_sec: int,
                 values: List[float]):
        self.workload_id = workload_id
        self.resource_name = resource_name
        self.start_time_epoch_sec = start_time_epoch_sec
        self.interval_sec = interval_sec
        self.values = values

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class GlobalResourceUsage:
    def __init__(self, resource_usages: Dict[str, Dict[str, List[float]]], usage_length: int = 60):
        """
        {
            <resource_name>: {
                <workload_id>: [<float>, <float>, ..., <float>],
                ...
            },
            ...
        }
        """
        self.__map = self.pad_usage(resource_usages, usage_length)

    def __get_resource_usage(self, resource_name: str) -> Optional[Dict[str, List[float]]]:
        return self.__map.get(resource_name, None)

    def __get_resource_usage_for_workload(self, resource_name: str, workload_id: str) -> Optional[List[float]]:
        usage = self.__get_resource_usage(resource_name)
        if usage is None:
            return None
        return usage.get(workload_id, None)

    @staticmethod
    def pad_usage(usage: Dict[str, Dict[str, List[float]]], usage_length):
        padded_usage = {}
        for resource_name, workload_usage in usage.items():
            padded_usage[resource_name] = {}
            for w_id, _ in workload_usage.items():
                padded_usage[resource_name][w_id] = []

        for resource_name, workload_usage in usage.items():
            for w_id, usage in workload_usage.items():
                pad_size = usage_length - len(usage)
                pad = [float('nan') for _ in range(pad_size)]
                d = deque(usage, maxlen=usage_length)
                d.extendleft(pad)
                padded_usage[resource_name][w_id] = list(d)

        return padded_usage

    def serialize(self) -> Dict[str, Dict[str, List[str]]]:
        s_map = {}
        for r_type, workload_usages in self.__map.items():
            s_map[r_type] = {}
            for w_id, values in workload_usages.items():
                s_map[r_type][w_id] = [str(v) for v in values]

        return s_map

    def get_all_usage_for_workload(self, workload_id) -> Dict[str, List[float]]:
        usages = {}
        for resource_name in RESOURCE_USAGE_NAMES:
            usage = self.__get_resource_usage_for_workload(resource_name, workload_id)
            if usage is not None:
                usages[resource_name] = usage

        return usages

    # CPU
    def get_cpu_usage(self) -> Optional[Dict[str, List[float]]]:
        return self.__get_resource_usage(CPU_USAGE)

    # MEM
    def get_mem_usage(self) -> Optional[Dict[str, List[float]]]:
        return self.__get_resource_usage(MEM_USAGE)

    # NET
    def get_net_recv_usage(self) -> Optional[Dict[str, List[float]]]:
        return self.__get_resource_usage(NET_RECV_USAGE)

    def get_net_trans_usage(self) -> Optional[Dict[str, List[float]]]:
        return self.__get_resource_usage(NET_TRANS_USAGE)

    # DISK
    def get_disk_usage(self) -> Optional[Dict[str, List[float]]]:
        return self.__get_resource_usage(DISK_USAGE)


def deserialize_global_resource_usage(s_map: Dict[str, Dict[str, List[str]]]) -> GlobalResourceUsage:
    d_map = {}
    usage_length = 60
    for r_type, workload_usages in s_map.items():
        d_map[r_type] = {}
        for w_id, values in workload_usages.items():
            usage_length = len(values)
            d_map[r_type][w_id] = [float(v) for v in values]

    return GlobalResourceUsage(d_map, usage_length)
