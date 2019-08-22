import calendar
from typing import Tuple, List

from titus_isolate.monitor.usage.usage_snapshot import UsageSnapshot


class MemUsage:

    def __init__(self, user: int):
        self.user = user


class MemUsageSnapshot(UsageSnapshot):

    def __init__(self, timestamp, usage: MemUsage):
        self.timestamp = timestamp
        self.usage = usage

    def get_column(self) -> Tuple[float, List[float]]:
        timestamp = calendar.timegm(self.timestamp.timetuple())
        column = [self.usage.user]
        return timestamp, column
