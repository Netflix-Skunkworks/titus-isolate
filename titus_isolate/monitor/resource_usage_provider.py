from typing import List


class ResourceUsage:

    def __init__(self, workload_id, resource_name, start_time_epoch_sec: float, interval_sec: int, values: List[float]):
        self.workload_id = workload_id
        self.resource_name = resource_name
        self.start_time_epoch_sec = start_time_epoch_sec
        self.interval_sec = interval_sec
        self.values = values
