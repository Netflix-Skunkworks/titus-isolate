import datetime
import os
from typing import Union

from titus_isolate import log
from titus_isolate.cgroup.utils import parse_cpuacct_usage_all, CPU_CPUACCT, MEMORY, get_usage_path
from titus_isolate.monitor.content import ContentSnapshot
from titus_isolate.monitor.cpu_usage import CpuUsageSnapshot
from titus_isolate.monitor.mem_usage import MemUsageSnapshot, MemUsage
from titus_isolate.monitor.resource_usage import ResourceUsageSnapshot


class CgroupMetricsProvider:

    def __init__(self, workload):
        self.__workload = workload
        self.__usage_path = {
            CPU_CPUACCT: None,
            MEMORY: None
        }

    def get_workload(self):
        return self.__workload

    def get_resource_usage(self) -> Union[ResourceUsageSnapshot, None]:
        cpu = self.get_cpu_usage()
        mem = self.get_mem_usage()

        if cpu is None or mem is None:
            return None

        return ResourceUsageSnapshot(cpu, mem)

    def get_cpu_usage(self) -> Union[CpuUsageSnapshot, None]:
        snapshot = self.__get_content_snapshot(CPU_CPUACCT)
        if snapshot is None:
            return None

        cpu_usage_rows = parse_cpuacct_usage_all(snapshot.content)
        return CpuUsageSnapshot(snapshot.timestamp, cpu_usage_rows)

    def get_mem_usage(self) -> Union[MemUsageSnapshot, None]:
        snapshot = self.__get_content_snapshot(MEMORY)
        if snapshot is None:
            return None

        return MemUsageSnapshot(snapshot.timestamp, MemUsage(int(snapshot.content)))

    def __get_content_snapshot(self, resource_key) -> Union[ContentSnapshot, None]:
        usage_path = self.__get_usage_path(resource_key)
        if usage_path is None:
            return None

        with open(usage_path, 'r') as f:
            timestamp = datetime.datetime.utcnow()
            content = f.read()
            return ContentSnapshot(timestamp, content)

    def __get_usage_path(self, resource_key) -> Union[str, None]:
        usage_path = self.__usage_path[resource_key]
        if usage_path is not None:
            return usage_path

        try:
            self.__usage_path[resource_key] = get_usage_path(self.__workload.get_id(), resource_key)
        except FileNotFoundError:
            log.warning("No '{}' path for workload: '{}'".format(resource_key, self.__workload.get_id()))
            return None

        if not os.path.isfile(usage_path):
            log.warning("{} usage path does not exist: {}".format(resource_key, usage_path))
            return None

        return self.__usage_path[resource_key]
