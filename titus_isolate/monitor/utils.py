from typing import List

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE
from titus_isolate.model.duration_prediction import DurationPrediction

from titus_isolate.monitor.resource_usage import ResourceUsage

CPU_USAGE_HEADING = 'cgroup.cpuacct.usage'
MEM_USAGE_HEADING = 'titus.memory.usage'
NET_RECV_USAGE_HEADING = 'titus.network.in.bytes'
NET_TRANS_USAGE_HEADING = 'titus.network.out.bytes'
DISK_USAGE_HEADING = 'titus.disk.bytes_used'

RESOURCE_HEADING_MAPPINGS = {
    CPU_USAGE_HEADING: CPU_USAGE,
    MEM_USAGE_HEADING: MEM_USAGE,
    NET_RECV_USAGE_HEADING: NET_RECV_USAGE,
    NET_TRANS_USAGE_HEADING: NET_TRANS_USAGE,
    DISK_USAGE_HEADING: DISK_USAGE,
}


def get_duration_predictions(input_str: str) -> List[DurationPrediction]:
    try:
        # "0.05=0.29953;0.1=0.29953;0.15=0.29953;0.2=0.29953;0.25=0.29953;0.3=0.29953;0.35=0.29953;0.4=0.29953;0.45=0.29953;0.5=0.29953;0.55=0.29953;0.6=0.29953;0.65=0.29953;0.7=0.29953;0.75=0.29953;0.8=0.29953;0.85=0.29953;0.9=0.29953;0.95=0.29953"
        duration_predictions = []
        pairs = input_str.split(';')
        for p in pairs:
            k, v = p.split('=')
            duration_predictions.append(DurationPrediction(float(k), float(v)))

        return duration_predictions
    except Exception:
        log.error("Failed to parse duration predictions: '{}'".format(input_str))
        return []


def resource_usages_to_dict(usages: List[ResourceUsage]) -> dict:
    d = {}
    for u in usages:
        if u.resource_name not in d:
            d[u.resource_name] = {}
        d[u.resource_name][u.workload_id] = [str(v) for v in u.values]

    return d
