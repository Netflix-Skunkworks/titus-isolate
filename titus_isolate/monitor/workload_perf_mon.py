import calendar
import collections
from math import ceil
from threading import Lock
from typing import List

import numpy as np

from titus_isolate import log
from titus_isolate.monitor.usage_snapshot import UsageSnapshot
from titus_isolate.monitor.utils import normalize_data


class WorkloadPerformanceMonitor:

    def __init__(self, metrics_provider, sample_frequency_sec):
        self.__metrics_provider = metrics_provider
        self.__sample_frequency_sec = sample_frequency_sec
        # Maintain buffers for the last hour
        self.__max_buffer_size = ceil(60 * 60 / sample_frequency_sec)
        self.__snapshot_lock = Lock()
        self.__snapshots = collections.deque([], self.__max_buffer_size)

    def get_workload(self):
        return self.__metrics_provider.get_workload()

    def sample(self):
        res_snap = self.__metrics_provider.get_resource_usage()
        if res_snap is None:
            log.debug("No resource usage snapshot available for workload: '{}'".format(self.get_workload().get_id()))
            return

        with self.__snapshot_lock:
            self.__snapshots.append(res_snap)
            log.debug("Took snapshot of metrics for workload: '{}'".format(self.get_workload().get_id()))

    def get_cpu_usage(self, seconds, agg_granularity_secs=60) -> List[float]:
        num_buckets = self.__get_num_buckets(seconds, agg_granularity_secs)
        timestamps, buffers = self._get_cpu_buffers()
        return normalize_data(timestamps, buffers, num_buckets, agg_granularity_secs)

    def get_mem_usage(self, seconds, agg_granularity_secs=60) -> List[float]:
        num_buckets = self.__get_num_buckets(seconds, agg_granularity_secs)
        timestamps, buffers = self._get_mem_buffers()
        return normalize_data(timestamps, buffers, num_buckets, agg_granularity_secs)

    def _get_cpu_buffers(self):
        with self.__snapshot_lock:
            cpu_snapshots = [s.cpu for s in self.__snapshots]
            return self.__get_buffers(cpu_snapshots, self.__max_buffer_size)

    def _get_mem_buffers(self):
        with self.__snapshot_lock:
            mem_snapshots = [s.mem for s in self.__snapshots]
            return self.__get_buffers(mem_snapshots, self.__max_buffer_size)

    def __get_num_buckets(self, seconds, agg_granularity_secs=60) -> int:
        num_buckets = ceil(seconds / agg_granularity_secs)
        if num_buckets > self.__max_buffer_size:
            raise Exception("Aggregation buffer too small to satisfy query.")

        return num_buckets

    @staticmethod
    def __get_buffers(snapshots: List[UsageSnapshot], max_buffer_size):
        if len(snapshots) == 0:
            return [], []

        _, first_column = snapshots[0].get_column()
        column_height = len(first_column)
        buffers = [collections.deque([], max_buffer_size) for _ in range(column_height)]
        timestamps = collections.deque([], max_buffer_size)

        for s in snapshots:
            timestamp, column = s.get_column()
            timestamps.append(timestamp)
            for i, row in enumerate(column):
                buffers[i].append(row)

        return np.array(timestamps, dtype=np.int32), [list(e) for e in buffers]
