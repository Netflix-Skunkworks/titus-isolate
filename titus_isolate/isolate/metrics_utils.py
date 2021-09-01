from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread


def get_allocated_size(cpu: Cpu) -> int:
    return len([t for t in cpu.get_threads() if t.is_claimed()])


def get_unallocated_size(cpu: Cpu) -> int:
    return len([t for t in cpu.get_threads() if not t.is_claimed()])


def get_oversubscribed_thread_count(cpu: Cpu) -> int:
    oversubscribed_thread_count = 0
    for t in cpu.get_threads():
        workloads_on_thread_count = len(t.get_workload_ids())
        if workloads_on_thread_count > 1:
            oversubscribed_thread_count += workloads_on_thread_count - 1

    return oversubscribed_thread_count


def _is_thread_occupied(thread: Thread, workload_map: dict, w_type: str) -> bool:
    for w_id in thread.get_workload_ids():
        if w_id in workload_map:
            if workload_map[w_id].get_type() == w_type:
                return True

    return False
