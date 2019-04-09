from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.utils import get_burst_workloads, is_thread_occupied


def get_allocated_size(cpu: Cpu) -> int:
    return len([t for t in cpu.get_threads() if t.is_claimed()])


def get_unallocated_size(cpu: Cpu) -> int:
    return len([t for t in cpu.get_threads() if not t.is_claimed()])


def get_burst_request_size(workloads: list) -> int:
    burst_request_size = 0
    for w in get_burst_workloads(workloads):
        burst_request_size += w.get_thread_count()

    return burst_request_size


def get_burst_allocated_size(cpu: Cpu, workload_map: dict) -> int:
    return _get_allocated_size(cpu, workload_map, BURST)


def get_static_allocated_size(cpu: Cpu, workload_map: dict) -> int:
    return _get_allocated_size(cpu, workload_map, STATIC)


def _get_allocated_size(cpu: Cpu, workload_map: dict, w_type: str) -> int:
    allocation_size = 0
    for t in cpu.get_threads():
        if is_thread_occupied(t, workload_map, w_type):
            allocation_size += 1

    return allocation_size


def get_oversubscribed_thread_count(cpu: Cpu, workload_map: dict) -> int:
    oversubscribed_thread_count = 0
    for t in cpu.get_threads():
        if is_thread_occupied(t, workload_map, BURST) and is_thread_occupied(t, workload_map, STATIC):
            oversubscribed_thread_count += 1

    return oversubscribed_thread_count


