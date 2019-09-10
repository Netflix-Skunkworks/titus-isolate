import os
from typing import List

from titus_isolate.allocate.constants import CPU, METADATA, TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL, CELL, \
    CPU_ALLOCATOR, ALLOCATOR_SERVICE_TASK_ID, UNKNOWN_ALLOCATOR_SERVICE_TASK_ID, TITUS_TASK_ID, CPU_ARRAY, \
    WORKLOAD_ALLOCATIONS
from titus_isolate.allocate.utils import parse_cpu
from titus_isolate.allocate.workload_allocate_response import WorkloadAllocateResponse
from titus_isolate.model.processor.cpu import Cpu


class AllocateResponse:

    def __init__(
            self,
            cpu: Cpu,  # TODO: Cpu is now deprecated
            workload_allocations: List[WorkloadAllocateResponse],
            cpu_allocator_name: str,
            metadata: dict = {}):
        self.__cpu = cpu
        self.__workload_allocations = workload_allocations
        self.__metadata = metadata
        self.__metadata[CPU_ALLOCATOR] = cpu_allocator_name
        if ALLOCATOR_SERVICE_TASK_ID not in self.__metadata:
            alloc_service_id = os.environ.get(TITUS_TASK_ID, UNKNOWN_ALLOCATOR_SERVICE_TASK_ID)
            self.__metadata[ALLOCATOR_SERVICE_TASK_ID] = alloc_service_id

    def get_cpu(self) -> Cpu:
        return self.__cpu

    def get_metadata(self) -> dict:
        return self.__metadata

    def to_dict(self) -> dict:
        return {
            CPU: self.get_cpu().to_dict(),
            WORKLOAD_ALLOCATIONS: self.__workload_allocations.to_dict(),
            CPU_ARRAY: self.get_cpu().to_array(),
            METADATA: self.get_metadata()
        }


def deserialize_response(headers, body) -> AllocateResponse:
    cell = headers.get(TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL)
    cpu = parse_cpu(body[CPU])
    metadata = body[METADATA]
    metadata[CELL] = cell
    cpu_allocator_name = metadata[CPU_ALLOCATOR]
    return AllocateResponse(cpu, cpu_allocator_name, metadata)
