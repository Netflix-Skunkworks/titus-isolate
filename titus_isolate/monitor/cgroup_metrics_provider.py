import datetime
import os
from typing import Union, Tuple

from titus_isolate import log
from titus_isolate.cgroup.utils import parse_cpuacct_usage_all, CPU_CPUACCT, MEMORY, get_usage_path, NET_RECV
from titus_isolate.monitor.content import ContentSnapshot
from titus_isolate.monitor.usage.cpu_usage import CpuUsageSnapshot
from titus_isolate.monitor.usage.mem_usage import MemUsageSnapshot, MemUsage
from titus_isolate.monitor.usage.net_usage import NetUsageSnapshot, NetUsage, RECV, TRANS
from titus_isolate.monitor.usage.resource_usage import ResourceUsageSnapshot


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
        net_recv, net_trans = self.get_net_usage()

        if None in [cpu, mem, net_recv, net_trans]:
            return None

        return ResourceUsageSnapshot(
            cpu=cpu,
            mem=mem,
            net_recv=net_recv,
            net_trans=net_trans)

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

    def get_net_usage(self) -> Union[Tuple[NetUsageSnapshot, NetUsageSnapshot], Tuple[None, None]]:
        # Inter-|   Receive                                                |  Transmit
        #  face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
        # metadataservice:    1146      15    0    0    0     0          0         0     1146      15    0    0    0     0       0          0
        #     lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
        #   eth0:  584261    4785    0    0    0     0          0       508   944760    5666    0    0    0     0       0          0

        net_dev_path = "/var/lib/titus-inits/{}/net/dev".format(self.__workload.get_id)
        eth0_key = "eth0:"
        recv_index = 1
        trans_index = 9

        with open(net_dev_path, 'r') as f:
            timestamp = datetime.datetime.utcnow()
            lines = f.readlines()
            for line in lines:
                tokens = line.split()
                if tokens[0] == eth0_key:
                    recv_usage = NetUsage(RECV, float(tokens[recv_index]))
                    trans_usage = NetUsage(TRANS, float(tokens[trans_index]))
                    return NetUsageSnapshot(timestamp, recv_usage), NetUsageSnapshot(timestamp, trans_usage)

        return None, None

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
