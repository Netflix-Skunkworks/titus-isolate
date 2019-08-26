import json
import re
import time

from typing import Dict

from titus_isolate import log
from titus_isolate.allocate.constants import FREE_THREAD_IDS
from titus_isolate.cgroup.utils import get_json_path, get_env_path, wait_for_file_to_exist
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.model.constants import WORKLOAD_ENV_LINE_REGEXP, WORKLOAD_ENV_CPU_KEY, WORKLOAD_ENV_MEM_KEY, \
    WORKLOAD_ENV_DISK_KEY, WORKLOAD_ENV_NETWORK_KEY, WORKLOAD_JSON_APP_NAME_KEY, WORKLOAD_JSON_PASSTHROUGH_KEY, \
    WORKLOAD_JSON_OWNER_KEY, WORKLOAD_JSON_IMAGE_KEY, WORKLOAD_JSON_IMAGE_DIGEST_KEY, WORKLOAD_JSON_PROCESS_KEY, \
    WORKLOAD_JSON_COMMAND_KEY, WORKLOAD_JSON_ENTRYPOINT_KEY, WORKLOAD_JSON_JOB_TYPE_KEY, WORKLOAD_JSON_CPU_BURST_KEY, \
    WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY, WORKLOAD_ENV_WAIT_TIMEOUT_SECONDS, WORKLOAD_JSON_WAIT_TIMEOUT_SECONDS, \
    WORKLOAD_JSON_READ_ATTEMPTS, WORKLOAD_JSON_READ_SLEEP_SECONDS
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider

def _wait_for_workload_files(identifier):
    start_time = time.time()
    wait_for_file_to_exist(get_env_path(identifier), WORKLOAD_ENV_WAIT_TIMEOUT_SECONDS, start_time=start_time)
    wait_for_file_to_exist(get_json_path(identifier), WORKLOAD_JSON_WAIT_TIMEOUT_SECONDS, start_time=start_time)


def get_workload_from_disk(identifier):
    _wait_for_workload_files(identifier)

    # in theory these files could go away if the task dies. that is ok. a failure here will only result in the workload
    # not being created which is fine because it is dead anyways.
    json_data = __get_workload_json(identifier)
    env_data = __get_workload_env(identifier) # note that this is string -> string

    cpus = int(env_data[WORKLOAD_ENV_CPU_KEY])
    mem = int(env_data[WORKLOAD_ENV_MEM_KEY])
    disk = int(env_data[WORKLOAD_ENV_DISK_KEY])
    network = int(env_data[WORKLOAD_ENV_NETWORK_KEY])
    app_name = json_data[WORKLOAD_JSON_APP_NAME_KEY]
    owner_email = json_data[WORKLOAD_JSON_PASSTHROUGH_KEY][WORKLOAD_JSON_OWNER_KEY]
    image = '{}@{}'.format(json_data[WORKLOAD_JSON_IMAGE_KEY], json_data[WORKLOAD_JSON_IMAGE_DIGEST_KEY])
    command = None
    if WORKLOAD_JSON_COMMAND_KEY in json_data[WORKLOAD_JSON_PROCESS_KEY]:
        command = json_data[WORKLOAD_JSON_PROCESS_KEY][WORKLOAD_JSON_COMMAND_KEY]
    entrypoint = None
    if WORKLOAD_JSON_ENTRYPOINT_KEY in json_data[WORKLOAD_JSON_PROCESS_KEY]:
        entrypoint = json_data[WORKLOAD_JSON_PROCESS_KEY][WORKLOAD_JSON_ENTRYPOINT_KEY]
    job_type = json_data[WORKLOAD_JSON_PASSTHROUGH_KEY][WORKLOAD_JSON_JOB_TYPE_KEY]
    workload_type = STATIC
    if json_data[WORKLOAD_JSON_CPU_BURST_KEY]:
        workload_type = BURST
    opportunistic_cpus = -1
    if WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY in json_data[WORKLOAD_JSON_PROCESS_KEY]:
        opportunistic_cpus = json_data[WORKLOAD_JSON_PASSTHROUGH_KEY][WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY]

    return Workload(
        identifier=identifier,
        thread_count=cpus,
        mem=mem,
        disk=disk,
        network=network,
        app_name=app_name,
        owner_email=owner_email,
        image=image,
        command=command,
        entrypoint=entrypoint,
        job_type=job_type,
        workload_type=workload_type,
        opportunistic_thread_count=opportunistic_cpus)


def __get_workload_json(identifier):
    for attempt in range(WORKLOAD_JSON_READ_ATTEMPTS):
        try:
            with open(get_json_path(identifier)) as json_file:
                return json.load(json_file)
        except json.decoder.JSONDecodeError as err:
            log.error("failed to read container %s json %s, retrying in %d seconds: %s", identifier,
                      get_json_path(identifier), WORKLOAD_JSON_READ_SLEEP_SECONDS, err)
        else:
            break
        time.sleep(WORKLOAD_JSON_READ_SLEEP_SECONDS)
    else:
        raise TimeoutError("failed to read container {} json {} after {} attempts".format(
            identifier, get_json_path(identifier), WORKLOAD_JSON_READ_ATTEMPTS))


def __get_workload_env(identifier):
    env = {}
    with open(get_env_path(identifier)) as env_file:
        line = env_file.readline()
        while line:
            match = re.match(WORKLOAD_ENV_LINE_REGEXP, line)
            if match is None:
                continue
            env[match.group(1)] = match.group(2)
            line = env_file.readline()
    return env


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


def update_burst_workloads(
        cpu: Cpu,
        workload_map: Dict[str, Workload],
        free_thread_provider: FreeThreadProvider,
        metadata: dict):

    free_threads = free_thread_provider.get_free_threads(cpu, workload_map)
    metadata[FREE_THREAD_IDS] = [t.get_id() for t in free_threads]

    burst_workloads = get_burst_workloads(workload_map.values())
    if len(burst_workloads) == 0:
        return

    for t in free_threads:
        for w in burst_workloads:
            t.claim(w.get_id())


def rebalance(cpu: Cpu, workloads: dict, free_thread_provider: FreeThreadProvider, metadata: dict) -> Cpu:
    burst_workloads = get_burst_workloads(workloads.values())
    release_all_threads(cpu, burst_workloads)
    update_burst_workloads(cpu, workloads, free_thread_provider, metadata)

    return cpu
