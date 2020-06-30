from threading import Lock

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE
from titus_isolate.config.constants import DEFAULT_SAMPLE_FREQUENCY_SEC, METRICS_QUERY_TIMEOUT_KEY, \
    DEFAULT_METRICS_QUERY_TIMEOUT_SEC
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.metrics.constants import BURST_POOL_USAGE_KEY, STATIC_POOL_USAGE_KEY
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.monitor.pcp_resource_usage_provider import PcpResourceUsageProvider
from titus_isolate.monitor.resource_usage import GlobalResourceUsage
from titus_isolate.monitor.utils import resource_usages_to_dict
from titus_isolate.utils import get_workload_manager, get_config_manager


class WorkloadMonitorManager(MetricsReporter):

    def __init__(
            self,
            seconds: int = 3600,
            agg_granularity_seconds: int = 60,
            sample_interval=DEFAULT_SAMPLE_FREQUENCY_SEC):

        self.__seconds = seconds
        self.__agg_granularity_seconds = agg_granularity_seconds
        self.__sample_interval = sample_interval

        self.__registry = None

        self.__lock = Lock()

        self.__usage_lock = Lock()

        metrics_query_timeout_sec = get_config_manager().get_int(
            METRICS_QUERY_TIMEOUT_KEY,
            DEFAULT_METRICS_QUERY_TIMEOUT_SEC)

        pcp_extra_time_sec = 2 * 60  # Two extra minutes to ensure full metrics buckets and no trailing nan
        self.__pcp_usage_provider = PcpResourceUsageProvider(
            relative_start_sec=seconds + pcp_extra_time_sec,
            interval_sec=agg_granularity_seconds,
            sample_interval_sec=sample_interval,
            query_timeout_sec=metrics_query_timeout_sec)

    def get_pcp_usage(self) -> dict:
        return resource_usages_to_dict(self.__pcp_usage_provider.get_resource_usages())

    def get_resource_usage(self) -> GlobalResourceUsage:
        return GlobalResourceUsage(self.get_pcp_usage())

    def set_registry(self, registry, tags):
        self.__registry = registry

    def report_metrics(self, tags):
        if self.__registry is None:
            log.debug("Not reporting metrics because there's no registry available yet.")
            return

        wm = get_workload_manager()
        if wm is None:
            log.debug("Not reporting metrics because there's no workload manager available yet.")
            return

        pcp_usage = self.get_pcp_usage()
        if CPU_USAGE not in pcp_usage.keys():
            log.warning("No CPU usage in PCP usage.")
            return

        usage = pcp_usage[CPU_USAGE]
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
                pool_cpu_usage += float(usage[len(usage) - 1])

        return pool_cpu_usage

    @staticmethod
    def __get_workloads():
        wm = get_workload_manager()
        if wm is None:
            log.debug("Workload manager not yet present.")
            return []

        return wm.get_workloads()
