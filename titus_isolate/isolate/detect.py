from functools import reduce

from titus_isolate.model.processor.utils import get_packages_with_workload, get_workload_ids


def get_cross_package_violations(cpu):
    """
    Returns a dictionary mapping workload ids to lists of package ids.  Only workloads on more than one package are
    included.

    {
       fa873f01-da52-45b4-b37b-edad0dfab519: []
    }

    :param cpu: CPU to scan for cross package violations
    :return: dictionary mapping workload ids to lists of packages
    """
    violations = {}
    workload_ids = get_workload_ids(cpu)

    for workload_id in workload_ids:
        packages = get_packages_with_workload(cpu, workload_id)
        if len(packages) > 1:
            violations[workload_id] = [p.get_id() for p in packages]

    return violations


def get_shared_core_violations(cpu):
    """
    Returns a dictionary mapping core ids to lists of workload ids.  Only workloads on more than one package are
    included.

    {
       12: [c520b163-daec-4c54-a835-585ba05915ca , c8c23650-d37f-4270-b36e-b74d27dfa709],
       <core_id>: [<workload_id>, <workload_id>]
       ...
    }

    :param cpu: CPU to scan for cross package violations
    :return: dictionary mapping core ids to lists of workload ids
    """
    violations = {}

    for package in cpu.get_packages():
        for core in package.get_cores():
            unique_workload_ids = set(__get_workload_ids(core))
            if len(unique_workload_ids) > 1:
                violation_key = ':'.join([str(package.get_id()), str(core.get_id())])
                violations[violation_key] = list(unique_workload_ids)

    return violations


def __get_workload_ids(core):
    workload_ids = []
    for t in core.get_threads():
        workload_ids += t.get_workload_ids()

    return workload_ids
