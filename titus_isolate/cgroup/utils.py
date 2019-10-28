import os
import time
from typing import List

from titus_isolate import log
from titus_isolate.monitor.usage.cpu_usage import CpuUsage

ROOT_CGROUP_PATH = "/sys/fs/cgroup"
TITUS_INITS_PATH = "/var/lib/titus-inits"
TITUS_ENVIRONMENTS_PATH = "/var/lib/titus-environments"

CPUSET = "cpuset"

CPU_CPUACCT = "cpu,cpuacct"
CPUACCT_USAGE_FILE = "cpuacct.usage_all"

MEMORY = "memory"
MEMORY_USAGE_FILE = "memory.usage_in_bytes"

USAGE_FILE = {
    CPU_CPUACCT: CPUACCT_USAGE_FILE,
    MEMORY: MEMORY_USAGE_FILE
}


def get_info_path(container_name):
    return "{}/{}/cgroup".format(TITUS_INITS_PATH, container_name)


def get_json_path(container_name):
    return "{}/{}.json".format(TITUS_ENVIRONMENTS_PATH, container_name)


def get_env_path(container_name):
    return "{}/{}.env".format(TITUS_ENVIRONMENTS_PATH, container_name)


def __noop():
    pass


def wait_for_file_to_exist(path, timeout, check_func=__noop, start_time=None):
    if start_time is None:
        start_time = time.time()

    log.debug("Waiting '{}' seconds from {} for file to exist: '{}'".format(timeout, start_time, path))
    while not os.path.exists(path):
        time.sleep(0.1)

        check_func()

        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            raise TimeoutError(
                "Expected file '{}' was not created in '{}' seconds.".format(path, timeout))


def _get_cgroup_path_from_list(cgroups_list, cgroup_name):
    for row in cgroups_list:
        r = row.split(":")
        name = r[1]
        path = r[2]

        if name == cgroup_name:
            return path.strip()

    return None


def get_cgroup_path_from_file(file_path, cgroup_name):
    log.debug("Reading '{}' path from file: '{}'".format(cgroup_name, file_path))
    with open(file_path, "r") as myfile:
        data = myfile.readlines()
        return _get_cgroup_path_from_list(data, cgroup_name)


def get_cpuset_path(container_name):
    file_path = get_info_path(container_name)
    cgroup_path = get_cgroup_path_from_file(file_path, CPUSET)
    return "{}/cpuset{}/cpuset.cpus".format(ROOT_CGROUP_PATH, cgroup_path)


def get_quota_path(container_name):
    file_path = get_info_path(container_name)
    cgroup_path = get_cgroup_path_from_file(file_path, CPU_CPUACCT)
    return "{}/cpu,cpuacct{}/cpu.cfs_quota_us".format(ROOT_CGROUP_PATH, cgroup_path)


def get_shares_path(container_name):
    file_path = get_info_path(container_name)
    cgroup_path = get_cgroup_path_from_file(file_path, CPU_CPUACCT)
    return "{}/cpu,cpuacct{}/cpu.shares".format(ROOT_CGROUP_PATH, cgroup_path)


def get_usage_path(container_name, resource_key):
    file_path = get_info_path(container_name)
    cgroup_path = get_cgroup_path_from_file(file_path, resource_key)
    usage_file = USAGE_FILE[resource_key]
    return "{}/{}{}/{}".format(ROOT_CGROUP_PATH, resource_key, cgroup_path, usage_file)


def set_cpuset(container_name, threads_str):
    path = get_cpuset_path(container_name)
    __write(path, threads_str)


def get_cpuset(container_name):
    path = get_cpuset_path(container_name)
    return __read(path)


def set_quota(container_name, value):
    path = get_quota_path(container_name)
    __write(path, value)


def get_quota(container_name):
    path = get_quota_path(container_name)
    return __read(path)


def set_shares(container_name, value):
    path = get_shares_path(container_name)
    __write(path, value)


def get_shares(container_name):
    path = get_shares_path(container_name)
    return __read(path)


def __write(path, value):
    log.debug("Writing '{}' to path '{}'".format(value, path))
    with open(path, 'w') as f:
        f.write(str(value))


def __read(path) -> str:
    log.debug("Reading from path '{}'".format(path))
    with open(path, 'r') as f:
        return f.readline().strip()


def parse_cpuacct_usage_all(text) -> List[CpuUsage]:
    # Text looks like this:
    #
    #     cpu user system
    #     0 0 0
    #     1 0 0
    #     2 73169258935876 0
    #     3 0 0
    #     ...
    #
    # so we skip the first line and return a list of lists

    #raw_rows = [line.split() for line in text.splitlines()[1:]]

    usage_rows = []
    for ind, row in enumerate(text.splitlines()):
        if ind == 0:
            continue
        cpu, user, system = row.split()
        usage_rows.append(CpuUsage(int(cpu), int(user), int(system)))

    return usage_rows


def parse_cpuset(cpuset_str: str) -> List[int]:
    ranges = list(x.split("-") for x in cpuset_str.split(","))
    if len(ranges) == 0:
        return []
    else:
        return list([i for r in ranges for i in range(int(r[0]), int(r[-1]) + 1)])
