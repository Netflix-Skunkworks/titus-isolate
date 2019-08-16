class MemUsage:

    def __init__(self, user: int):
        self.user = user


class MemUsageSnapshot:

    def __init__(self, timestamp, usage: MemUsage):
        self.timestamp = timestamp
        self.usage = usage


