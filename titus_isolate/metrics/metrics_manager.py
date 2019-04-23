import os

import schedule
from spectator import GlobalRegistry

from titus_isolate import log
from titus_isolate.allocate.constants import UNKNOWN_CPU_ALLOCATOR, CELL, CPU_ALLOCATOR
from titus_isolate.utils import get_workload_manager, get_cell_name

registry = GlobalRegistry


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

        tags[CPU_ALLOCATOR] = allocator_name
        tags[CELL] = get_cell_name()

        return tags

