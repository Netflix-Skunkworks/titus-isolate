class CpuUsageSnapshot:

    def __init__(self, timestamp, rows):
        self.timestamp = timestamp
        self.rows = rows


class CpuUsage:

    def __init__(self, pu_id, user, system):
        self.pu_id = pu_id
        self.user = user
        self.system = system
