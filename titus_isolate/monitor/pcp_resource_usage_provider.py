import subprocess
from threading import Lock
from typing import List

import schedule

from titus_isolate import log
from titus_isolate.config.constants import DEFAULT_SAMPLE_FREQUENCY_SEC, DEFAULT_METRICS_QUERY_TIMEOUT_SEC
from titus_isolate.monitor.resource_usage import ResourceUsage
from titus_isolate.monitor.utils import get_resource_usage, get_pcp_archive_path
from titus_isolate.utils import get_workload_manager, is_kubernetes


class PcpResourceUsageProvider:

    def __init__(
            self,
            relative_start_sec: int,
            interval_sec: int,
            sample_interval_sec: int = DEFAULT_SAMPLE_FREQUENCY_SEC,
            query_timeout_sec: int = DEFAULT_METRICS_QUERY_TIMEOUT_SEC):

        self.__relative_start_sec = relative_start_sec
        self.__interval_sec = interval_sec
        self.__query_timeout_sec = query_timeout_sec
        self.__interval_count = int(relative_start_sec / interval_sec)
        self.__raw_csv_snapshot = None
        self.__lock = Lock()
        self.__snapshot_usage_raw()

        log.info("Scheduling pcp metrics collecting every {} seconds".format(sample_interval_sec))
        schedule.every(sample_interval_sec).seconds.do(self.__snapshot_usage_raw)

    def __snapshot_usage_raw(self):
        try:
            # Avoid making a metrics query on a potentially empty dataset which causes the query command to fail, which
            # causes noisy logs which look like failures.
            workload_manager = get_workload_manager()
            if workload_manager is None or len(workload_manager.get_workloads()) == 0:
                log.info('No workloads so skipping pcp snapshot.')
                return

            instance_filter = "INVALID_INSTANCE_FILTER"
            if is_kubernetes():
                instance_filter = '.*titus-executor.*.service'
            else:
                instance_filter = '/containers.slice/[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}'

            # pmrep -a /var/log/pcp/pmlogger/$(hostname)/ -S -60m -t 1m -y s -o csv -i .*titus-executor.*.service  cgroup.cpuacct.usage cgroup.memory.usage
            snapshot_cmd_fmt = """ pmrep -a {0} \
                    -S -{1}s \
                    -T -0s \
                    -t {2}s \
                    -y s \
                    -o csv \
                    -i {3} \
                    cgroup.cpuacct.usage \
                    cgroup.memory.usage \
                    titus.network.in.bytes \
                    titus.network.out.bytes \
                    titus.disk.bytes_used """

            cmd_str = snapshot_cmd_fmt.format(
                get_pcp_archive_path(),
                self.__relative_start_sec,
                self.__interval_sec,
                instance_filter)

            log.info('Snapshoting usage from pcp: {}'.format(' '.join(cmd_str.split())))

            byte_array = subprocess.check_output(cmd_str, shell=True, timeout=self.__query_timeout_sec)

            with self.__lock:
                self.__raw_csv_snapshot = byte_array.decode('utf-8')
        except:
            log.exception("Failed to snapshot pcp raw data.")

    def get_resource_usages(self) -> List[ResourceUsage]:
        with self.__lock:
            try:
                log.debug('Computing usages from pcp snapshot: {}'.format(self.__raw_csv_snapshot))
                if self.__raw_csv_snapshot is not None:
                    usages = get_resource_usage(self.__raw_csv_snapshot, self.__interval_count, self.__interval_sec)
                    log.debug('usages: {}'.format(usages))
                    return usages
                else:
                    log.warning('No PCP resource CSV snapshot set')
                    return []
            except:
                log.exception("Failed to compute usages.")
