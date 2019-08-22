import calendar
from typing import Tuple, List

from titus_isolate.monitor.usage.usage_snapshot import UsageSnapshot

RECV = "recv"
TRANS = "trans"


class NetUsage:
    def __init__(self, usage_type: str, bytes: float):
        self.usage_type = usage_type
        self.bytes = bytes


class NetUsageSnapshot(UsageSnapshot):
    def __init__(self, timestamp, usage: NetUsage):
        self.timestamp = timestamp
        self.usage = usage

    def get_column(self) -> Tuple[float, List[float]]:
        timestamp = calendar.timegm(self.timestamp.timetuple())
        column = [self.usage.bytes]
        return timestamp, column
