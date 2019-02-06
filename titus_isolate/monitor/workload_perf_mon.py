import collections
from threading import Lock

from titus_isolate import log

MAX_COUNTER_BUFFER_SIZE = 600
TIMESTAMP = "timestamp"


class WorkloadPerformanceMonitor:

    def __init__(self, metrics_provider, sample_frequency_sec):
        self.__metrics_provider = metrics_provider
        self.__sample_frequency_sec = sample_frequency_sec
        self.__buffer_lock = Lock()
        self.__buffers = {
            TIMESTAMP: collections.deque([], MAX_COUNTER_BUFFER_SIZE)
        }

    def get_workload(self):
        return self.__metrics_provider.get_workload()

    def get_buffers(self):
        with self.__buffer_lock:
            copy = {}
            for key, buffer in self.__buffers.items():
                copy[key] = list(buffer)
            return copy

    def get_cpu_usage(self, seconds):
        sample_count = int(seconds) // self.__sample_frequency_sec

        buffers = self.get_buffers()
        end = len(buffers[TIMESTAMP]) - 1
        start = end - sample_count

        # Insufficient samples to satisfy request
        if start < 0:
            log.debug(
                "Insufficient samples to calculate cpu usage over the last '{}' seconds for workload: '{}'".format(
                seconds, self.get_workload().get_id()))
            return None

        end_time = buffers[TIMESTAMP][end]
        start_time = buffers[TIMESTAMP][start]
        diff = end_time - start_time
        wall_time_ns = diff.total_seconds() * 1000000000

        cpu_usage = collections.OrderedDict()
        for pu_id, buffer in sorted(buffers.items()):
            if pu_id == TIMESTAMP:
                continue
            cpu_time_ns = buffer[end] - buffer[start]
            cpu_usage[pu_id] = cpu_time_ns / wall_time_ns

        return cpu_usage

    def sample(self):
        cpu_usage_snapshot = self.__metrics_provider.get_cpu_usage()
        if cpu_usage_snapshot is None:
            log.debug("No cpu usage snapshot available for workload: '{}'".format(self.get_workload().get_id()))
            return

        with self.__buffer_lock:
            if len(self.__buffers) == 1:
                self.__init_buffers(len(cpu_usage_snapshot.rows))

            self.__buffers[TIMESTAMP].append(cpu_usage_snapshot.timestamp)
            for row in cpu_usage_snapshot.rows:
                self.__buffers[str(row.pu_id)].append(int(row.user) + int(row.system))

            log.debug("Took snapshot of metrics for workload: '{}'".format(self.get_workload().get_id()))

    def __init_buffers(self, count):
        for x in range(count):
            self.__buffers[str(x)] = collections.deque([], MAX_COUNTER_BUFFER_SIZE)
