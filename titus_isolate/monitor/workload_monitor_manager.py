import collections
from threading import Lock

import schedule

from titus_isolate import log
from titus_isolate.monitor.cgroup_metrics_provider import CgroupMetricsProvider
from titus_isolate.monitor.workload_perf_mon import WorkloadPerformanceMonitor

DEFAULT_SAMPLE_FREQUENCY_SEC = 6


class WorkloadMonitorManager:

    def __init__(self, workload_manager, sample_interval=DEFAULT_SAMPLE_FREQUENCY_SEC):
        self.__workload_manager = workload_manager
        self.__lock = Lock()
        self.__monitors = {}

        schedule.every(sample_interval).seconds.do(self.__sample)

    def get_monitors(self):
        return self.__monitors

    def to_dict(self):
        with self.__lock:
            monitors_dict = {}
            for workload_id, monitor in sorted(self.get_monitors().items()):
                buffers = collections.OrderedDict()
                for key, deque in sorted(monitor.get_raw_buffers().items()):
                    lst = list(deque)
                    lst = [str(i) for i in lst]
                    buffers[key] = lst
                monitors_dict[workload_id] = buffers

            return monitors_dict

    def __sample(self):
        try:
            self.__update_monitors()
            self.__sample_monitors()
        except:
            log.exception("Failed to sample performance monitors.")

    def __update_monitors(self):
        workloads = self.__workload_manager.get_workloads()

        with self.__lock:
            # Remove monitors for workloads which are no longer managed
            workload_ids = [w.get_id() for w in workloads]
            for monitored_id in list(self.__monitors.keys()):
                if monitored_id not in workload_ids:
                    self.__monitors.pop(monitored_id, None)

            # Add monitors for new workloads
            for workload in workloads:
                if workload.get_id() not in self.__monitors.keys():
                    self.__monitors[workload.get_id()] = WorkloadPerformanceMonitor(CgroupMetricsProvider(workload))

    def __sample_monitors(self):
        with self.__lock:
            for workload_id, monitor in self.__monitors.items():
                try:
                    monitor.sample()
                except:
                    log.exception("Failed to sample performance of workload: '{}'".format(workload_id))
