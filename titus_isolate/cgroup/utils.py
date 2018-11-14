import os
import time

from titus_isolate.utils import get_logger

ROOT_CGROUP_PATH = "/sys/fs/cgroup"
ROOT_MESOS_INFO_PATH = "/var/lib/titus-inits"
MAX_FILE_WAIT_S = 1


log = get_logger()


def wait_for_file_to_exist(file_path):
    start_time = time.time()

    while not os.path.exists(file_path):
        log.debug("Waiting for file to exist: '{}'".format(file_path))
        time.sleep(0.1)
        elapsed_time = time.time() - start_time

        if elapsed_time > MAX_FILE_WAIT_S:
            raise TimeoutError(
                "Expected file '{}' was not created in '{}' seconds.".format(file_path, MAX_FILE_WAIT_S))


def get_cpuset_path_from_list(cgroups_list):
    for row in cgroups_list:
        r = row.split(":")
        name = r[1]
        path = r[2]

        if name == "cpuset":
            return path.strip()

    return None


def get_cpuset_path_from_file(file_path):
    log.info("Reading cpuset path from file: '{}'".format(file_path))
    wait_for_file_to_exist(file_path)

    with open(file_path, "r") as myfile:
        data = myfile.readlines()
        return get_cpuset_path_from_list(data)


def get_cpuset_path(container_name):
    info_file_path = "{}/{}/cgroup".format(ROOT_MESOS_INFO_PATH, container_name)
    cpuset_file_path = get_cpuset_path_from_file(info_file_path)

    return "{}/cpuset{}/cpuset.cpus".format(ROOT_CGROUP_PATH, cpuset_file_path)


def set_cpuset(container_name, threads_str):
    path = get_cpuset_path(container_name)
    log.info("Writing '{}' to path '{}'".format(threads_str, path))

    with open(path, 'w') as f:
        f.write(threads_str)
