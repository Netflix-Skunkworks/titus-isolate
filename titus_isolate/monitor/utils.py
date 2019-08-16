import calendar
from typing import Dict, List
from datetime import datetime as dt

from titus_isolate import log
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload

import numpy as np


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


def normalize_data(timestamps, buffers, num_buckets=60, bucket_size_secs=60):
    proc_time = np.full((num_buckets,), np.nan, dtype=np.float32)

    if len(timestamps) == 0:
        return proc_time

    ts_max = timestamps[-1]

    for i in range(num_buckets):
        ts_min = ts_max - bucket_size_secs

        # get slice:
        slice_ts_min = np.searchsorted(timestamps, ts_min)
        slice_ts_max = np.searchsorted(timestamps, ts_max, 'right')
        if slice_ts_max == len(timestamps):
            slice_ts_max -= 1

        ts_max = ts_min

        if slice_ts_min == slice_ts_max:
            continue

        if slice_ts_min < 0 or slice_ts_min >= len(timestamps):
            continue

        if slice_ts_max < 0 or slice_ts_max >= len(timestamps):
            continue

        if timestamps[slice_ts_max] < ts_min - bucket_size_secs:
            continue
        # this should be matching Atlas:
        time_diff_ns = (timestamps[slice_ts_max] - timestamps[slice_ts_min]) * 1000000000
        s = 0.0
        for b in buffers:  # sum across all cpus
            s += b[slice_ts_max] - b[slice_ts_min]
        if time_diff_ns > 0:
            s /= time_diff_ns
        proc_time[num_buckets - 1 - i] = s

    return proc_time
