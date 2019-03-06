from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def get_sorted_workloads(workloads):
    return sorted(workloads, key=lambda w: w.get_creation_time())


def release_all_threads(cpu, workloads):
    for w in workloads:
        release_threads(cpu, w.get_id())


def release_threads(cpu, workload_id):
    for t in cpu.get_threads():
        t.free(workload_id)


def update_burst_workloads(cpu, burst_workloads, free_thread_provider):
    free_threads = free_thread_provider.get_free_threads(cpu)
    for t in free_threads:
        for w in burst_workloads:
            t.claim(w.get_id())


def rebalance(cpu: Cpu, workloads: dict, free_thread_provider: FreeThreadProvider) -> Cpu:
    burst_workloads = get_burst_workloads(workloads.values())
    release_all_threads(cpu, burst_workloads)
    update_burst_workloads(cpu, burst_workloads, free_thread_provider)

    return cpu
