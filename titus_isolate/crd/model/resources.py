import os

from titus_isolate import log
from titus_isolate.config.constants import EC2_INSTANCE_TYPE

CPU = 'cpu'
MEM = 'memMB'
NET = 'netMbps'
DISK = 'diskMB'
GPU = 'gpu'

machine_types = {
    "m5.metal": {CPU: 96, GPU: 0, MEM: 374784, DISK: 1637376, NET: 25000},
    "r5.metal": {CPU: 96, GPU: 0, MEM: 761856, DISK: 1571840, NET: 25000},
    "g4dn.metal": {CPU: 96, GPU: 8, MEM: 374784, DISK: 1571840, NET: 100000},
    "p3.16xlarge": {CPU: 64, GPU: 8, MEM: 480256, DISK: 1047552, NET: 25000},
    "g4dn.4xlarge": {CPU: 16, GPU: 1, MEM: 53453, DISK: 1047552, NET: 20000},
    "g4dn.8xlarge": {CPU: 32, GPU: 1, MEM: 115712, DISK: 1047552, NET: 50000},
    "r5.24xlarge": {CPU: 96, GPU: 0, MEM: 753664, DISK: 1571840, NET: 23000},
    "m5.24xlarge": {CPU: 96, GPU: 0, MEM: 366592, DISK: 1637376, NET: 23000},
}


class Resources:
    def __init__(self, cpu=0, mem=0, disk=0, net=0, gpu=0):
        self.cpu = cpu
        self.mem = mem
        self.disk = disk
        self.net = net
        self.gpu = gpu

    def __add__(self, other):
        return Resources(
            self.cpu + other.cpu,
            self.mem + other.mem,
            self.disk + other.disk,
            self.net + other.net,
            self.gpu + other.gpu
            )

    def populate_from_capacity_env(self):
        self.cpu = 0
        self.mem = 0
        self.disk = 0
        self.net = 0

        unknown = "UNKNOWN"
        instance_type = os.environ.get(EC2_INSTANCE_TYPE, unknown)

        if instance_type == unknown:
            log.error("Instance type environment variable not present: %s", EC2_INSTANCE_TYPE)
            return

        if instance_type not in machine_types:
            log.error("Unexpected instance type encountered: %s", instance_type)
            return

        machine = machine_types[instance_type]
        self.cpu = machine[CPU]
        self.mem = machine[MEM]
        self.disk = machine[DISK]
        self.net = machine[NET]
        self.gpu = machine[GPU]

        log.info("Loaded node capacity: %s", self.to_dict())

    def to_dict(self):
        return {
            CPU: self.cpu,
            MEM: self.mem,
            NET: self.net,
            DISK: self.disk,
            GPU: self.gpu
        }
