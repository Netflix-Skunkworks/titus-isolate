import datetime
import os

from titus_isolate import log
from titus_isolate.cgroup.utils import parse_cpuacct_usage_all, get_usage_all_path
from titus_isolate.monitor.cpu_usage import CpuUsageSnapshot


class CgroupMetricsProvider:

    def __init__(self, workload):
        self.__workload = workload
        self.__usage_path = None

    def get_workload(self):
        return self.__workload

    def get_cpu_usage(self):
        usage_path = self.__get_usage_path()
        if usage_path is None:
            return None

        if not os.path.isfile(usage_path):
            log.warning("cpu usage path does not exist: {}".format(usage_path))
            return

        with open(usage_path, 'r') as f:
            timestamp = datetime.datetime.utcnow()
            content = f.read()

        cpu_usage_rows = parse_cpuacct_usage_all(content)
        return CpuUsageSnapshot(timestamp, cpu_usage_rows)

    def __get_usage_path(self):
        if self.__usage_path is not None:
            return self.__usage_path

        try:
            self.__usage_path = get_usage_all_path(self.__workload.get_id())
        except FileNotFoundError:
            log.warning("No cpu usage path for workload: '{}'".format(self.__workload.get_id()))

        return self.__usage_path
