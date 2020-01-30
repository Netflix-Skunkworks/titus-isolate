import subprocess
from threading import Lock
from typing import List

import schedule

from titus_isolate import log
from titus_isolate.config.constants import DEFAULT_SAMPLE_FREQUENCY_SEC
from titus_isolate.monitor.resource_usage_provider import ResourceUsage
from titus_isolate.monitor.utils import get_resource_usage


class PcpResourceUsageProvider:

    def __init__(
            self,
            relative_start_sec: int,
            interval_sec: int,
            interval_count: int,
            archive_path: str,
            sample_interval: int = DEFAULT_SAMPLE_FREQUENCY_SEC):

        self.__relative_start_sec = relative_start_sec
        self.__interval_sec = interval_sec
        self.__interval_count = interval_count
        self.__archive_path = archive_path
        self.__raw_csv_snapshot = None
        self.__lock = Lock()
        self.__snapshot_usage_raw()

        schedule.every(sample_interval).seconds.do(self.__snapshot_usage_raw)
        schedule.every(sample_interval).seconds.do(self.get_resource_usages)

    def __snapshot_usage_raw(self) -> str:
        with self.__lock:
            # pmrep -a /var/log/pcp/pmlogger/$(hostname)/ -S -60m -t 1m -y s -o csv -i .*titus-executor.*.service  cgroup.cpuacct.usage cgroup.memory.usage
            snapshot_cmd_fmt = """ pmrep -a {0} \
                -S -{1}s \
                -t {2}s \
                -y s \
                -o csv \
                -i .*titus-executor.*.service \
                cgroup.cpuacct.usage \
                cgroup.memory.usage """

            cmd_str = snapshot_cmd_fmt.format(
                self.__archive_path,
                self.__relative_start_sec,
                self.__interval_sec)

            byte_array = subprocess.check_output(cmd_str, shell=True)
            self.__raw_csv_snapshot = byte_array.decode('utf-8')

    def get_resource_usages(self) -> List[ResourceUsage]:
        with self.__lock:
            usages = get_resource_usage(self.__raw_csv_snapshot, self.__interval_count, self.__interval_sec)
            log.info('usages: {}'.format(usages))
            return usages
