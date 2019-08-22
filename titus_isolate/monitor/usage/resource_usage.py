from titus_isolate.monitor.usage.cpu_usage import CpuUsageSnapshot
from titus_isolate.monitor.usage.mem_usage import MemUsageSnapshot
from titus_isolate.monitor.usage.net_usage import NetUsageSnapshot


class ResourceUsageSnapshot:

    def __init__(self,
                 cpu: CpuUsageSnapshot,
                 mem: MemUsageSnapshot,
                 net_recv: NetUsageSnapshot,
                 net_trans: NetUsageSnapshot):
        self.cpu = cpu
        self.mem = mem
        self.net_recv = net_recv
        self.net_trans = net_trans
