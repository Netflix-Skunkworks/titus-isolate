import os
from typing import List

from titus_isolate.allocate.constants import CPU, METADATA, TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL, CELL, \
    CPU_ALLOCATOR, ALLOCATOR_SERVICE_TASK_ID, UNKNOWN_ALLOCATOR_SERVICE_TASK_ID, TITUS_TASK_ID, CPU_ARRAY, \
    WORKLOAD_ALLOCATIONS
from titus_isolate.allocate.utils import parse_cpu
from titus_isolate.allocate.workload_allocate_response import WorkloadAllocateResponse, get_workload_response, \
    deserialize_workload_response
from titus_isolate.isolate.update import get_threads
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload, deserialize_workload


class AllocateResponse:

    def __init__(
            self,
            cpu: Cpu,
            workload_allocations: List[WorkloadAllocateResponse],
            cpu_allocator_name: str,
            metadata: dict = None):

        self.__cpu = cpu
        self.__workload_allocations = workload_allocations

        if metadata is None:
            metadata = {}
        self.__metadata = metadata
        self.__metadata[CPU_ALLOCATOR] = cpu_allocator_name

        if ALLOCATOR_SERVICE_TASK_ID not in self.__metadata:
            alloc_service_id = os.environ.get(TITUS_TASK_ID, UNKNOWN_ALLOCATOR_SERVICE_TASK_ID)
            self.__metadata[ALLOCATOR_SERVICE_TASK_ID] = alloc_service_id

    def get_cpu(self) -> Cpu:
        return self.__cpu

    def get_workload_allocations(self) -> List[WorkloadAllocateResponse]:
        return self.__workload_allocations

    def get_metadata(self) -> dict:
        return self.__metadata

    def to_dict(self) -> dict:
        return {
            CPU: self.get_cpu().to_dict(),
            WORKLOAD_ALLOCATIONS: [w.to_dict() for w in self.get_workload_allocations()],
            CPU_ARRAY: self.get_cpu().to_array(),
            METADATA: self.get_metadata()
        }


def get_workload_allocations(cpu: Cpu, workloads: List[Workload]) -> List[WorkloadAllocateResponse]:
    allocations = [get_workload_response(w, cpu) for w in workloads]
    return list([a for a in allocations if a is not None])


def deserialize_response(headers, body) -> AllocateResponse:
    cell = headers.get(TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL)
    cpu = parse_cpu(body[CPU])
    metadata = body[METADATA]
    metadata[CELL] = cell
    cpu_allocator_name = metadata[CPU_ALLOCATOR]
    workload_allocations = [deserialize_workload_response(w_alloc) for w_alloc in body[WORKLOAD_ALLOCATIONS]]
    return AllocateResponse(cpu, workload_allocations, cpu_allocator_name, metadata)
