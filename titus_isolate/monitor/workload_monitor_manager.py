import collections
from threading import Lock, Thread

import schedule

from titus_isolate import log
from titus_isolate.config.constants import DEFAULT_SAMPLE_FREQUENCY_SEC
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.metrics.constants import BURST_POOL_USAGE_KEY, STATIC_POOL_USAGE_KEY
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.monitor.cgroup_metrics_provider import CgroupMetricsProvider
from titus_isolate.monitor.cpu_usage_provider import CpuUsageProvider
from titus_isolate.monitor.workload_perf_mon import WorkloadPerformanceMonitor
from titus_isolate.utils import get_workload_manager


class WorkloadMonitorManager(CpuUsageProvider, MetricsReporter):

    def __init__(self, sample_interval=DEFAULT_SAMPLE_FREQUENCY_SEC):
        self.__sample_interval = sample_interval
        self.__lock = Lock()
        self.__monitors = {}
        self.__registry = None

        schedule.every(sample_interval).seconds.do(self.__sample)

    def get_cpu_usage(self, seconds: int, agg_granularity_secs: int) -> dict:
        with self.__lock:
            cpu_usage = {}
            for workload_id, monitor in self.get_monitors().items():
                cpu_usage[workload_id] = monitor.get_normalized_cpu_usage_last_seconds(seconds, agg_granularity_secs)

        return cpu_usage

    def set_registry(self, registry):
        self.__registry = registry

    def report_metrics(self, tags):
        if self.__registry is None:
            log.debug("Not reporting metrics because there's no registry available yet.")
            return

        wm = get_workload_manager()
        if wm is None:
            log.debug("Not reporting metrics because there's no workload manager available yet.")
            return

        usage = self.get_cpu_usage(60, 60)
        static_pool_cpu_usage = self.__get_pool_usage(STATIC, usage)
        burst_pool_cpu_usage = self.__get_pool_usage(BURST, usage)

        self.__registry.gauge(STATIC_POOL_USAGE_KEY, tags).set(static_pool_cpu_usage)
        self.__registry.gauge(BURST_POOL_USAGE_KEY, tags).set(burst_pool_cpu_usage)

    @staticmethod
    def __get_pool_usage(workload_type, usage):
        wm = get_workload_manager()
        if wm is None:
            log.debug("Not reporting metrics because there's no workload manager available yet.")
            return

        workload_map = wm.get_workload_map_copy()

        pool_cpu_usage = 0.0
        for w_id, usage in usage.items():
            if w_id not in workload_map:
                continue

            workload = workload_map[w_id]
            if workload.get_type() == workload_type:
                pool_cpu_usage += usage[len(usage) - 1]

        return pool_cpu_usage

    def get_monitors(self):
        return self.__monitors

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

    @staticmethod
    def __get_workloads():
        wm = get_workload_manager()
        if wm is None:
            log.debug("Workload manager not yet present.")
            return []

        return wm.get_workloads()

    def __update_monitors(self):
        workloads = self.__get_workloads()

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
                    Thread(target=monitor.sample).start()
                except:
                    log.exception("Failed to sample performance of workload: '{}'".format(workload_id))
