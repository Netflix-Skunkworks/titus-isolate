import os

RESOURCE_CPU_CAPACITY_ENV = 'CPU_CAPACITY'
RESOURCE_MEM_CAPACITY_ENV = 'MEMORY_CAPACITY'
RESOURCE_NET_CAPACITY_ENV = 'NETWORK_CAPACITY'
RESOURCE_DISK_CAPACITY_ENV = 'DISK_CAPACITY'

RESOURCE_CPU_CAPACITY_KEY = 'cpu'
RESOURCE_MEM_CAPACITY_KEY = 'memMB'
RESOURCE_NET_CAPACITY_KEY = 'netMbps'


class ResourcesCapacity:
    def __init__(self):
        self.cpu = int(os.environ.get(RESOURCE_CPU_CAPACITY_ENV, '0'))
        self.mem_MB = int(os.environ.get(RESOURCE_MEM_CAPACITY_ENV, '0'))
        self.disk_MB = int(os.environ.get(RESOURCE_DISK_CAPACITY_ENV, '0'))
        self.net_Mbps = int(os.environ.get(RESOURCE_NET_CAPACITY_ENV, '0'))

    def to_dict(self):
        return {
            RESOURCE_CPU_CAPACITY_KEY: self.cpu,
            RESOURCE_MEM_CAPACITY_KEY: self.mem_MB,
            RESOURCE_NET_CAPACITY_KEY: self.net_Mbps
        }