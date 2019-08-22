import calendar
import math
from typing import Dict, List, Tuple
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


def normalize_monotonic_data(timestamps, buffers, num_buckets=60, bucket_size_secs=60) -> List[float]:
    return __normalize_data(__get_monotonic_element, timestamps, buffers, num_buckets, bucket_size_secs)


def normalize_gauge_data(timestamps, buffers, num_buckets=60, bucket_size_secs=60) -> List[float]:
    return __normalize_data(__get_gauge_element, timestamps, buffers, num_buckets, bucket_size_secs)


def __normalize_data(get_element, timestamps, buffers, num_buckets, bucket_size_secs) -> List[float]:
    data = np.full((num_buckets,), np.nan, dtype=np.float32)
    if len(timestamps) == 0:
        return list(data.tolist())

    min_indices, max_indices = __get_bucket_indices(timestamps, num_buckets, bucket_size_secs)

    for i in range(len(min_indices)):
        min_index = min_indices[i]
        max_index = max_indices[i]

        if min_index < 0 or max_index < 0:
            continue

        data[i] = get_element(timestamps, buffers, min_index, max_index)

    return list(data.tolist())


def __get_monotonic_element(timestamps, buffers, min_index, max_index) -> float:
    time_diff_ns = (timestamps[max_index] - timestamps[min_index]) * 1000000000
    s = 0.0
    for b in buffers:
        s += b[max_index] - b[min_index]
    if time_diff_ns > 0:
        s /= time_diff_ns

    return s


def __get_gauge_element(timestamps, buffers, min_index, max_index) -> float:
    s = 0.0
    value_count = max_index - min_index + 1
    for b in buffers:
        for i in range(value_count):
            s += b[min_index + i]
    return s / value_count


def __get_bucket_indices(timestamps, num_buckets, bucket_size_secs) -> Tuple[List[int], List[int]]:
    min_indices = np.full((num_buckets,), np.nan, dtype=np.int32)
    max_indices = np.full((num_buckets,), np.nan, dtype=np.int32)

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

        min_indices[num_buckets - 1 - i] = slice_ts_min
        max_indices[num_buckets - 1 - i] = slice_ts_max

    min_indices = list(min_indices.tolist())
    max_indices = list(max_indices.tolist())
    return min_indices, max_indices

