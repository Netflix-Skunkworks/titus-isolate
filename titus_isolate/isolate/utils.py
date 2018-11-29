from titus_isolate.docker.constants import BURST, STATIC
from titus_isolate.isolate.cpu import assign_threads


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def assign_workload(new_cpu, workload):
    if workload.get_type() != STATIC:
        return

    return assign_threads(new_cpu, workload)
