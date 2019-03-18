import os

import schedule
from spectator import GlobalRegistry

from titus_isolate import log
from titus_isolate.isolate.utils import get_allocator
from titus_isolate.utils import get_config_manager

registry = GlobalRegistry


class MetricsManager:

    def __init__(self, reporters, reg=registry, report_interval=60):
        self.__reporters = reporters
        self.__reg = reg

        for reporter in self.__reporters:
            reporter.set_registry(self.__reg)

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

        allocator_name = get_allocator(get_config_manager()).get_primary_allocator().__class__.__name__
        tags["cpu_allocator"] = allocator_name

        return tags
