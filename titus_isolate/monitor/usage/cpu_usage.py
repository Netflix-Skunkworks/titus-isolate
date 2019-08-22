import calendar
from typing import Tuple, List

from titus_isolate.monitor.usage.usage_snapshot import UsageSnapshot


class CpuUsage:

    def __init__(self, pu_id, user, system):
        self.pu_id = pu_id
        self.user = user
        self.system = system


class CpuUsageSnapshot(UsageSnapshot):

    def __init__(self, timestamp, rows):
        self.timestamp = timestamp
        self.rows = rows

    def get_column(self) -> Tuple[float, List[float]]:
        timestamp = calendar.timegm(self.timestamp.timetuple())
        column = [int(r.user) + int(r.system) for r in self.rows]
        return timestamp, column
