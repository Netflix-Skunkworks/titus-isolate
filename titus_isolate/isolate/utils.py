from titus_isolate.docker.constants import BURST, STATIC


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]
