import copy

from titus_isolate.allocate.allocate_request import AllocateRequest, deserialize_allocate_request
from titus_isolate.allocate.constants import WORKLOAD_ID
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.monitor.resource_usage import GlobalResourceUsage


class AllocateThreadsRequest(AllocateRequest):

    def __init__(self, cpu: Cpu, workload_id: str, workloads: dict, metadata: dict):
        """
        A threads request encapsulates all information needed to assign threads to workloads when a workload is being
        added or removed.
        """
        super().__init__(
            cpu=cpu,
            workloads=workloads,
            metadata=metadata)
        self.__workload_id = copy.deepcopy(workload_id)

    def get_workload_id(self):
        return self.__workload_id

    def to_dict(self):
        d = super().to_dict()
        d[WORKLOAD_ID] = self.get_workload_id()
        return d


def deserialize_allocate_threads_request(serialized_request: dict) -> AllocateThreadsRequest:
    allocate_request = deserialize_allocate_request(serialized_request)
    workload_id = serialized_request[WORKLOAD_ID]
    return AllocateThreadsRequest(
        cpu=allocate_request.get_cpu(),
        workload_id=workload_id,
        workloads=allocate_request.get_workloads(),
        metadata=allocate_request.get_metadata())
