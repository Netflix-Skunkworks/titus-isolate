from typing import List, Dict, Union, Set

from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE, \
    RESOURCE_USAGE_NAMES


class ResourceUsage:

    def __init__(self, workload_id: str, resource_name: str, start_time_epoch_sec: float, interval_sec: int, values: List[float]):
        self.workload_id = workload_id
        self.resource_name = resource_name
        self.start_time_epoch_sec = start_time_epoch_sec
        self.interval_sec = interval_sec
        self.values = values

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class GlobalResourceUsage:
    def __init__(self, resource_usages: Dict[str, Dict[str, List[float]]]):
        """
        {
            <resource_name>: {
                <workload_id>: [<float>, <float>, ..., <float>],
                ...
            },
            ...
        }
        """
        self.__map = resource_usages

    def __get_resource_usage(self, resource_name: str) -> Union[Dict[str, List[float]], None]:
        return self.__map.get(resource_name, None)

    def __get_resource_usage_for_workload(self, resource_name: str, workload_id: str) -> Union[List[float], None]:
        usage = self.__get_resource_usage(resource_name)
        if usage is None:
            return None
        return usage.get(workload_id, None)

    def serialize(self) -> Dict[str, Dict[str, List[str]]]:
        s_map = {}
        for r_type, workload_usages in self.__map.items():
            s_map[r_type] = {}
            for w_id, values in workload_usages.items():
                s_map[r_type][w_id] = [str(v) for v in values]

        return s_map

    def get_workload_ids(self) -> Set[str]:
        ids = set()
        for r_name, workload_usages in self.__map.items():
            for w_id, _ in workload_usages.items():
                ids.add(w_id)
        return ids

    def get_all_usage_for_workload(self, workload_id) -> Dict[str, List[float]]:
        usages = {}
        for resource_name in RESOURCE_USAGE_NAMES:
            usage = self.__get_resource_usage_for_workload(resource_name, workload_id)
            if usage is not None:
                usages[resource_name] = usage

        return usages

    def get_cpu_usage(self) -> Union[Dict[str, List[float]], None]:
        return self.__get_resource_usage(CPU_USAGE)

    def get_cpu_usage_for_workload(self, workload_id: str) -> Union[List[float], None]:
        return self.__get_resource_usage_for_workload(CPU_USAGE, workload_id)

    # MEM
    def get_mem_usage(self) -> Union[Dict[str, List[float]], None]:
        return self.__get_resource_usage(MEM_USAGE)

    def get_mem_usage_for_workload(self, workload_id: str) -> Union[List[float], None]:
        return self.__get_resource_usage_for_workload(MEM_USAGE, workload_id)

    # NET
    def get_net_recv_usage(self) -> Union[Dict[str, List[float]], None]:
        return self.__get_resource_usage(NET_RECV_USAGE)

    def get_net_recv_usage_for_workload(self, workload_id: str) -> Union[List[float], None]:
        return self.__get_resource_usage_for_workload(NET_RECV_USAGE, workload_id)

    def get_net_trans_usage(self) -> Union[Dict[str, List[float]], None]:
        return self.__get_resource_usage(NET_TRANS_USAGE)

    def get_net_trans_usage_for_workload(self, workload_id: str) -> Union[List[float], None]:
        return self.__get_resource_usage_for_workload(NET_TRANS_USAGE, workload_id)

    # DISK
    def get_net_disk_usage(self) -> Union[Dict[str, List[float]], None]:
        return self.__get_resource_usage(DISK_USAGE)

    def get_net_disk_usage_for_workload(self, workload_id: str) -> Union[List[float], None]:
        return self.__get_resource_usage_for_workload(DISK_USAGE, workload_id)


def deserialize_global_resource_usage(s_map: Dict[str, Dict[str, List[str]]]) -> GlobalResourceUsage:
    d_map = {}
    for r_type, workload_usages in s_map.items():
        d_map[r_type] = {}
        for w_id, values in workload_usages.items():
            d_map[r_type][w_id] = [float(v) for v in values]

    return GlobalResourceUsage(d_map)



