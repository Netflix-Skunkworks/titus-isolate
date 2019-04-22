import os

import requests
import schedule
from spectator import GlobalRegistry

from titus_isolate import log
from titus_isolate.allocate.constants import UNKNOWN_CPU_ALLOCATOR
from titus_isolate.config.constants import REMOTE_ALLOCATOR_URL
from titus_isolate.utils import get_workload_manager, get_config_manager

registry = GlobalRegistry


def get_cell_name():
    unknown_cell = "unknown_cell"
    titus_isolate_cell_header = "X-Titus-Isolate-Cell"

    config_manager = get_config_manager()
    if config_manager is None:
        log.warning("Config manager is not yet set.")
        return unknown_cell

    url = config_manager.get_str(REMOTE_ALLOCATOR_URL)
    if url is None:
        log.warning("No remote solver URL specified.")
        return unknown_cell

    try:
        response = requests.get(url, timeout=1)
        cell_name = response.headers.get(titus_isolate_cell_header, None)
        if cell_name is None:
            log.warning("Titus isolation cell header is not set.")
            return unknown_cell
        else:
            return cell_name
    except:
        log.exception("Failed to determine isolation cell.")
        return unknown_cell


class MetricsManager:

    def __init__(self, reporters, reg=registry, report_interval=60):
        self.__reporters = reporters
        self.__reg = reg

        for reporter in self.__reporters:
            reporter.set_registry(self.__reg)

        log.info("Scheduling metrics reporting every {} seconds".format(report_interval))
        schedule.every(report_interval).seconds.do(self.__report_metrics)

    def __report_metrics(self):
        try:
            tags = self.__get_tags()

            for reporter in self.__reporters:
                reporter.report_metrics(tags)
        except:
            log.exception("Failed to report metrics.")

    @staticmethod
    def __get_tags():
        ec2_instance_id = 'EC2_INSTANCE_ID'

        tags = {}
        if ec2_instance_id in os.environ:
            tags["node"] = os.environ[ec2_instance_id]
            tags["nf.node"] = os.environ[ec2_instance_id]

        wm = get_workload_manager()
        if wm is None:
            allocator_name = UNKNOWN_CPU_ALLOCATOR
        else:
            allocator_name = wm.get_allocator_name()

        tags["cpu_allocator"] = allocator_name
        tags["cell"] = get_cell_name()

        return tags

