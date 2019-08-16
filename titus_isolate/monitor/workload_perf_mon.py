import calendar
import collections
from datetime import datetime as dt
from math import ceil
from threading import Lock

import numpy as np

from titus_isolate import log
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

    def _get_cpu_buffers(self):
        with self.__snapshot_lock:
            if len(self.__snapshots) == 0:
                return [], []

            # The number of threads per sample is constant across all samples
            thread_count = len(self.__snapshots[0].cpu.rows)
            buffers = [collections.deque([], self.__max_buffer_size) for _ in range(thread_count)]
            timestamps = collections.deque([], self.__max_buffer_size)

            for res_snap in self.__snapshots:
                timestamps.append(res_snap.cpu.timestamp)
                for row in res_snap.cpu.rows:
                    buffers[row.pu_id].append(int(row.user) + int(row.system))

            return np.array([calendar.timegm(t.timetuple()) for t in timestamps], dtype=np.int32), \
                   [list(e) for e in buffers]

    def get_cpu_usage(self, seconds, agg_granularity_secs=60):
        num_buckets = ceil(seconds / agg_granularity_secs)
        if num_buckets > self.__max_buffer_size:
            raise Exception("Aggregation buffer too small to satisfy query.")

        timestamps, buffers = self._get_cpu_buffers()
        return normalize_data(timestamps, buffers, num_buckets, agg_granularity_secs)
