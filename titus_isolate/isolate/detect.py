from titus_isolate.model.processor.utils import get_workload_ids, get_packages_with_workload


def get_cross_package_violations(cpu):
    workload_ids = get_workload_ids(cpu)
    violations = {}

    for workload_id in workload_ids:
        packages = get_packages_with_workload(cpu, workload_id)
        if len(packages) > 1:
            violations[workload_id] = packages

    return violations
