import collections
from threading import Lock

from titus_isolate import log

from titus_isolate.config.constants import DEFAULT_SAMPLE_FREQUENCY_SEC

# Maintain buffers for the last hour
MAX_COUNTER_BUFFER_SIZE = int(60 * 60 / DEFAULT_SAMPLE_FREQUENCY_SEC)
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

    def get_processing_time_ns(self, seconds):
        buffers, start, end = self.__get_buffers_start_end(seconds)

        if buffers is None:
            log.debug(
                "Insufficient samples to calculate processing time for workload: '{}'".format(
                    self.get_workload().get_id()))
            return None

        return self.__get_processing_time(buffers, start, end)

    def get_cpu_usage(self, seconds):
        buffers, start, end = self.__get_buffers_start_end(seconds)

        if buffers is None:
            log.debug(
                "Insufficient samples to calculate cpu usage for workload: '{}'".format(self.get_workload().get_id()))
            return None

        end_time = buffers[TIMESTAMP][end]
        start_time = buffers[TIMESTAMP][start]
        diff = end_time - start_time
        wall_time_ns = diff.total_seconds() * 1000000000

        processing_time = self.__get_processing_time(buffers, start, end)

        cpu_usage = collections.OrderedDict()
        for pu_id, proc_time in processing_time.items():
            cpu_usage[pu_id] = proc_time / wall_time_ns

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

    def __get_buffers_start_end(self, seconds):
        sample_count = int(seconds) // self.__sample_frequency_sec

        buffers = self.get_buffers()
        end = len(buffers[TIMESTAMP]) - 1
        start = end - sample_count

        # Insufficient samples to satisfy request
        if start < 0:
            log.debug("Insufficient samples to provide buffers over the last '{}' seconds".format(seconds))
            return None, None, None

        return buffers, start, end

    @staticmethod
    def __get_processing_time(buffers, start, end):
        processing_time = collections.OrderedDict()
        for pu_id, buffer in sorted(buffers.items()):
            if pu_id == TIMESTAMP:
                continue
            cpu_time_ns = buffer[end] - buffer[start]
            processing_time[pu_id] = cpu_time_ns

        return processing_time
