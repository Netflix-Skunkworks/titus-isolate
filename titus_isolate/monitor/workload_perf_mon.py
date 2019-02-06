import collections
from threading import Lock

from titus_isolate import log

MAX_COUNTER_BUFFER_SIZE = 600
TIMESTAMP = "timestamp"


class WorkloadPerformanceMonitor:

    def __init__(self, metrics_provider):
        self.__metrics_provider = metrics_provider
        self.__buffer_lock = Lock()
        self.__buffers = {
            TIMESTAMP: collections.deque([], MAX_COUNTER_BUFFER_SIZE)
        }

    def get_workload(self):
        return self.__metrics_provider.get_workload()

    def get_raw_buffers(self):
        with self.__buffer_lock:
            return self.__buffers

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
