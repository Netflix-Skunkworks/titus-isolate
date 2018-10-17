from titus_isolate.model.processor.utils import get_workload_ids, get_packages_with_workload


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
    workload_ids = get_workload_ids(cpu)
    violations = {}

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
       fa873f01-da52-45b4-b37b-edad0dfab519: []
    }

    :param cpu: CPU to scan for cross package violations
    :return: dictionary mapping workload ids to lists of packages
    """
