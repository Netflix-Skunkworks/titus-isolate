from titus_isolate.monitor.cpu_usage import CpuUsageSnapshot
from titus_isolate.monitor.mem_usage import MemUsageSnapshot


class ResourceUsageSnapshot:

    def __init__(self, cpu: CpuUsageSnapshot, mem: MemUsageSnapshot):
        self.cpu = cpu
        self.mem = mem
