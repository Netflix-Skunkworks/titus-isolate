import os
from titus_isolate.allocate.constants import CPU, METADATA, TITUS_ISOLATE_CELL_HEADER, UNKNOWN_CELL, CELL, \
    CPU_ALLOCATOR, ALLOCATOR_SERVICE_TASK_ID, UNKNOWN_ALLOCATOR_SERVICE_TASK_ID, TITUS_TASK_ID, CPU_ARRAY
from titus_isolate.allocate.utils import parse_cpu
from titus_isolate.model.processor.cpu import Cpu


class AllocateResponse:

    def __init__(self, cpu: Cpu, cpu_allocator_name: str, metadata: dict = {}):
        self.__cpu = cpu
        self.__metadata = metadata
        self.__metadata[CPU_ALLOCATOR] = cpu_allocator_name
        if ALLOCATOR_SERVICE_TASK_ID not in self.__metadata:
            alloc_service_id = os.environ.get(TITUS_TASK_ID, UNKNOWN_ALLOCATOR_SERVICE_TASK_ID)
            self.__metadata[ALLOCATOR_SERVICE_TASK_ID] = alloc_service_id

    def get_cpu(self):
        return self.__cpu

    def get_metadata(self):
        return self.__metadata

    def to_dict(self):
        return {
            CPU: self.get_cpu().to_dict(),
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
