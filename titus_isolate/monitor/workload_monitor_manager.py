import collections
from threading import Lock

import schedule

from titus_isolate import log
from titus_isolate.config.constants import DEFAULT_SAMPLE_FREQUENCY_SEC
from titus_isolate.monitor.cgroup_metrics_provider import CgroupMetricsProvider
from titus_isolate.monitor.cpu_usage_provider import CpuUsageProvider
from titus_isolate.monitor.workload_perf_mon import WorkloadPerformanceMonitor
from titus_isolate.utils import get_workload_manager


class WorkloadMonitorManager(CpuUsageProvider):

    def __init__(self, sample_interval=DEFAULT_SAMPLE_FREQUENCY_SEC):
        self.__sample_interval = sample_interval
        self.__lock = Lock()
        self.__monitors = {}

        schedule.every(sample_interval).seconds.do(self.__sample)

    def get_monitors(self):
        return self.__monitors

    def get_cpu_usage(self, seconds: int, agg_granularity_secs: int) -> dict:
        cpu_usage = {}
        for workload_id, monitor in self.get_monitors().items():
            cpu_usage[workload_id] = monitor.get_normalized_cpu_usage_last_seconds(seconds, agg_granularity_secs)

        return cpu_usage

    def to_dict(self):
        with self.__lock:
            monitors_dict = {}
            for workload_id, monitor in sorted(self.get_monitors().items()):
                buffers = collections.OrderedDict()
                _, timestamps, mon_buffers = monitor.get_buffers()
                for cpu_ind, buff in enumerate(mon_buffers):
                    buffers[str(cpu_ind)] = [str(i) for i in buff]
                buffers['timestamps'] = timestamps
                monitors_dict[workload_id] = buffers

            return monitors_dict

    def __sample(self):
        try:
            self.__update_monitors()
            self.__sample_monitors()
        except:
            log.exception("Failed to sample performance monitors.")

    def __update_monitors(self):
        wm = get_workload_manager()
        if wm is None:
            log.debug("Workload manager not yet present.")
            return

        workloads = wm.get_workloads()

        with self.__lock:
            # Remove monitors for workloads which are no longer managed
            workload_ids = [w.get_id() for w in workloads]
            for monitored_id in list(self.__monitors.keys()):
                if monitored_id not in workload_ids:
                    self.__monitors.pop(monitored_id, None)

            # Add monitors for new workloads
            for workload in workloads:
                if workload.get_id() not in self.__monitors:
                    self.__monitors[workload.get_id()] = \
                        WorkloadPerformanceMonitor(CgroupMetricsProvider(workload), self.__sample_interval)

    def __sample_monitors(self):
        with self.__lock:
            for workload_id, monitor in self.__monitors.items():
                try:
                    monitor.sample()
                except:
                    log.exception("Failed to sample performance of workload: '{}'".format(workload_id))
