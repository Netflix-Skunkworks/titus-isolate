import os
import time

from titus_isolate import log

ROOT_CGROUP_PATH = "/sys/fs/cgroup"
ROOT_MESOS_INFO_PATH = "/var/lib/titus-inits"

CPUSET = "cpuset"
CPU_CPUACCT = "cpu,cpuacct"


def wait_for_file_to_exist(file_path, timeout):
    start_time = time.time()

    while not os.path.exists(file_path):
        log.debug("Waiting for file to exist: '{}'".format(file_path))
        time.sleep(0.1)
        elapsed_time = time.time() - start_time

        if elapsed_time > timeout:
            raise TimeoutError(
                "Expected file '{}' was not created in '{}' seconds.".format(file_path, timeout))


def _get_cgroup_path_from_list(cgroups_list, cgroup_name):
    for row in cgroups_list:
        r = row.split(":")
        name = r[1]
        path = r[2]

        if name == cgroup_name:
            return path.strip()

    return None


def get_cgroup_path_from_file(file_path, cgroup_name, timeout):
    log.debug("Reading '{}' path from file: '{}'".format(cgroup_name, file_path))
    wait_for_file_to_exist(file_path, timeout)

    with open(file_path, "r") as myfile:
        data = myfile.readlines()
        return _get_cgroup_path_from_list(data, cgroup_name)


def __get_info_path(container_name):
    return "{}/{}/cgroup".format(ROOT_MESOS_INFO_PATH, container_name)


def get_cpuset_path(container_name, timeout):
    info_file_path = __get_info_path(container_name)
    cgroup_path = get_cgroup_path_from_file(info_file_path, CPUSET, timeout)

    return "{}/cpuset{}/cpuset.cpus".format(ROOT_CGROUP_PATH, cgroup_path)


def get_quota_path(container_name, timeout):
    info_file_path = __get_info_path(container_name)
    cgroup_path = get_cgroup_path_from_file(info_file_path, CPU_CPUACCT, timeout)

    return "{}/cpu,cpuacct{}/cpu.cfs_quota_us".format(ROOT_CGROUP_PATH, cgroup_path)


def set_cpuset(container_name, threads_str, timeout):
    path = get_cpuset_path(container_name, timeout)

    orig_quota = get_quota(container_name, timeout)
    log.info("Saved quota: '{}' for: '{}'".format(orig_quota, container_name))
    set_quota(container_name, -1, timeout)

    log.info("Writing '{}' to path '{}'".format(threads_str, path))
    with open(path, 'w') as f:
        f.write(threads_str)

    set_quota(container_name, orig_quota, timeout)


def set_quota(container_name, value, timeout):
    path = get_quota_path(container_name, timeout)

    log.info("Writing '{}' to path '{}'".format(value, path))
    with open(path, 'w') as f:
        f.write(str(value))


def get_quota(container_name, timeout):
    path = get_quota_path(container_name, timeout)

    log.info("Reading from path '{}'".format(path))
    with open(path, 'r') as f:
        return int(f.readline().strip())
