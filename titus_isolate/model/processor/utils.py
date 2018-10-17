def get_empty_threads(threads):
    return [t for t in threads if not t.is_claimed()]


# Workloads
def get_workload_ids(cpu):
    return [thread.get_workload_id() for thread in cpu.get_threads() if thread.is_claimed()]


def get_packages_with_workload(cpu, workload_id):
    return [package for package in cpu.get_packages() if is_on_package(package, workload_id)]


def is_on_package(package, workload_id):
    return len(get_threads_with_workload(package, workload_id)) > 0


def get_cores_with_workload(package, workload_id):
    return [core for core in package.get_cores() if is_on_core(core, workload_id)]


def is_on_core(core, workload_id):
    return len(get_threads_with_workload(core, workload_id)) > 0


def get_threads_with_workload(core, workload_id):
    return [thread for thread in core.get_threads() if thread.get_workload_id() == workload_id]
