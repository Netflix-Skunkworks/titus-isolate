import csv
import re
import socket
from collections import deque

from datetime import datetime
from io import StringIO
from typing import Dict, List, Tuple, Union

import pytz

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE
from titus_isolate.event.constants import STATIC
from titus_isolate.model.duration_prediction import DurationPrediction
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload_interface import Workload

from titus_isolate.monitor.resource_usage import ResourceUsage
from titus_isolate.utils import is_kubernetes

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


def get_free_cores(
        threshold: float,
        cpu: Cpu,
        workload_map: Dict[str, Workload],
        cpu_usage: Dict[str, float]) -> List[Core]:
    return [c for c in cpu.get_cores() if is_core_below_threshold(threshold, c, cpu_usage, workload_map)]


def is_core_below_threshold(
        threshold: float,
        core: Core,
        workload_usage: Dict[str, float],
        workload_map: Dict[str, Workload]):

    # Get all workload IDs running on this core
    workload_ids = []
    for t in core.get_threads():
        workload_ids += t.get_workload_ids()

    # Measure the usage of all _static_ workloads running on this core in proportion to their requested thread count.
    #
    # e.g.
    # w_id  | usage
    #    a  |    2%
    #    b  |    3%
    #    c  |    1%
    # -------------
    # total |    6%
    usage = 0
    for w_id in workload_ids:
        workload = workload_map.get(w_id, None)
        if workload is not None and workload.get_type() == STATIC:
            usage += workload_usage.get(w_id, workload.get_thread_count()) / workload.get_thread_count()

    # If we set the threshold to 10% and continue the example above
    #
    # e.g.
    # is_free = 6% <= 10%
    # is_free = true
    is_free = usage <= threshold

    if is_free:
        log.debug("Core: {} with usage: {} is UNDER threshold: {}".format(core.get_id(), usage, threshold))
    else:
        log.debug("Core: {} with usage: {} is OVER  threshold: {}".format(core.get_id(), usage, threshold))

    return is_free


def parse_usage_csv(csv_raw: str) -> Union[Dict[str, List], None]:
    # Time,"cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service","cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7aad3fa0-b172-496e-87cd-032bff7daba1.service","cgroup.memory.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service","cgroup.memory.usage-/containers.slice/titus-executor@default__7aad3fa0-b172-496e-87cd-032bff7daba1.service"
    # 2020-01-29 19:46:32,,,8343552,10649600
    # 2020-01-29 19:47:32,1.000,1.991,8343552,10649600
    # 2020-01-29 19:48:32,1.000,1.988,8343552,10649600
    # 2020-01-29 19:49:32,1.000,1.991,8343552,10649600
    # 2020-01-29 19:50:32,1.000,1.987,8343552,10649600

    f = StringIO(csv_raw)
    rows = list(csv.reader(f))

    if len(rows) <= 1:
        return None

    headings = rows[0]
    columns = [[] for _ in range(len(headings))]

    # Drop first row, we know the format
    for row in rows[1:]:
        for i, val in enumerate(row):
            columns[i].append(val)

    parsed = {}
    for i, col in enumerate(headings):
        parsed[col] = columns[i]

    return parsed


def pad_usage(parsed_csv: Dict[str, List], length: int = 60):
    padded = {}
    for k, v in parsed_csv.items():
        pad_size = length - len(v)
        pad = ['' for _ in range(pad_size)]
        d = deque(v, maxlen=length)
        d.extendleft(pad)
        padded[k] = list(d)

    return padded


def parse_mesos_csv_usage_heading(heading: str) -> Tuple[str, str]:
    # cgroup.cpuacct.usage-/containers.slice/dcc5ae03-745b-45b4-a759-5c63c4434a97
    regex = "([^\/]+$)"
    return __parse_csv_usage_heading(heading, regex)


def parse_kubernetes_csv_usage_heading(heading: str) -> Tuple[str, str]:
    # cgroup.cpuacct.usage-/containers.slice/titus-executor@default__7b1c435b-9473-40be-b944-2b0b26e2a703.service
    regex = "__(.*)\\.service"
    return __parse_csv_usage_heading(heading, regex)


def __parse_csv_usage_heading(heading: str, regex: str) -> Tuple[str, str]:
    resource_name, container_name = heading.split('-', maxsplit=1)
    workload_id = re.search(regex, container_name).group(1)

    return workload_id, RESOURCE_HEADING_MAPPINGS[resource_name]


def get_resource_usage(raw_csv_usage: str, value_count: int, interval_sec: int) -> List[ResourceUsage]:
    log.debug("raw: {}".format(raw_csv_usage))

    parsed = parse_usage_csv(raw_csv_usage)
    log.debug("parsed: {}".format(parsed))

    padded = pad_usage(parsed, value_count)
    log.debug("padded: {}".format(padded))

    TIME = 'Time'
    end_time = datetime.strptime(padded[TIME][-1], "%Y-%m-%d %H:%M:%S")
    end_time = pytz.utc.localize(end_time)
    end_time_epoch = datetime.timestamp(end_time)
    start_time_epoch = end_time_epoch - (value_count * interval_sec)

    usages = []
    for k, v in padded.items():
        if k == TIME:
            continue

        if is_kubernetes():
            w_id, resource_name = parse_kubernetes_csv_usage_heading(k)
        else:
            w_id, resource_name = parse_mesos_csv_usage_heading(k)

        values = [float('nan') if x == '' else float(x) for x in v]
        usage = ResourceUsage(w_id, resource_name, start_time_epoch, interval_sec, values)
        usages.append(usage)

    return usages


def get_pcp_archive_path() -> str:
    return "/mnt/pcp/pmlogger/{}/".format(socket.gethostname())


def resource_usages_to_dict(usages: List[ResourceUsage]) -> dict:
    d = {}
    for u in usages:
        if u.resource_name not in d:
            d[u.resource_name] = {}
        d[u.resource_name][u.workload_id] = [str(v) for v in u.values]

    return d
