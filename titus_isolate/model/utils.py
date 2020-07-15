import json
import re
import time

from typing import Dict, List, Optional

from titus_isolate import log
from titus_isolate.allocate.constants import FREE_THREAD_IDS
from titus_isolate.cgroup.utils import get_json_path, get_env_path
from titus_isolate.config.constants import GET_WORKLOAD_RETRY_COUNT, DEFAULT_GET_WORKLOAD_RETRY_COUNT, \
    GET_WORKLOAD_RETRY_INTERVAL_SEC, DEFAULT_GET_WORKLOAD_RETRY_INTERVAL_SEC
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.model.constants import *
from titus_isolate.model.kubernetes_workload import KubernetesWorkload
from titus_isolate.model.legacy_workload import LegacyWorkload
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider
from titus_isolate.monitor.utils import get_duration_predictions
from titus_isolate.utils import get_pod_manager, managers_are_initialized, get_config_manager


def get_duration(workload: Workload, percentile: float) -> Optional[float]:
    for p in workload.get_duration_predictions():
        if p.get_percentile() == percentile:
            return p.get_duration()

    return None


def get_workload_from_kubernetes(identifier) -> Optional[KubernetesWorkload]:
    if not managers_are_initialized():
        log.error("Cannot get workload from kubernetes because managers aren't initialized")
        return None

    retry_count = get_config_manager().get_int(GET_WORKLOAD_RETRY_COUNT, DEFAULT_GET_WORKLOAD_RETRY_COUNT)
    retry_interval = get_config_manager().get_int(GET_WORKLOAD_RETRY_INTERVAL_SEC, DEFAULT_GET_WORKLOAD_RETRY_INTERVAL_SEC)

    pod_manager = get_pod_manager()
    for i in range(retry_count):
        log.info("Getting pod from kubernetes: %s", identifier)
        pod = pod_manager.get_pod(identifier)
        if pod is not None:
            log.info("Got pod from kubernetes: %s", identifier)
            return KubernetesWorkload(pod)

        log.info("Retrying getting pod from kubernetes in %s seconds", retry_interval)
        time.sleep(retry_interval)

    log.error("Failed to get pod from kubernetes: %s", identifier)
    return None


def get_workload_from_disk(identifier) -> LegacyWorkload:
    # In theory these files could go away if the task dies. that is ok.  A failure here will only result in the workload
    # not being created which is fine because it is dead anyway.
    json_data = __get_workload_json(identifier)
    passthrough_data = json_data[WORKLOAD_JSON_PASSTHROUGH_KEY]
    env_data = __get_workload_env(identifier)  # note that this is string -> string

    launch_time = int(json_data[WORKLOAD_JSON_RUNSTATE_KEY][WORKLOAD_JSON_LAUNCHTIME_KEY])
    cpus = int(env_data[WORKLOAD_ENV_CPU_KEY])
    mem = int(env_data[WORKLOAD_ENV_MEM_KEY])
    disk = int(env_data[WORKLOAD_ENV_DISK_KEY])
    network = int(env_data[WORKLOAD_ENV_NETWORK_KEY])
    app_name = json_data[WORKLOAD_JSON_APP_NAME_KEY]
    owner_email = passthrough_data[WORKLOAD_JSON_OWNER_KEY]
    image = '{}@{}'.format(json_data[WORKLOAD_JSON_IMAGE_KEY], json_data[WORKLOAD_JSON_IMAGE_DIGEST_KEY])

    command = None
    if WORKLOAD_JSON_COMMAND_KEY in json_data[WORKLOAD_JSON_PROCESS_KEY]:
        command = json_data[WORKLOAD_JSON_PROCESS_KEY][WORKLOAD_JSON_COMMAND_KEY]

    entrypoint = None
    if WORKLOAD_JSON_ENTRYPOINT_KEY in json_data[WORKLOAD_JSON_PROCESS_KEY]:
        entrypoint = json_data[WORKLOAD_JSON_PROCESS_KEY][WORKLOAD_JSON_ENTRYPOINT_KEY]

    job_type = passthrough_data[WORKLOAD_JSON_JOB_TYPE_KEY]

    workload_type = STATIC
    if json_data[WORKLOAD_JSON_CPU_BURST_KEY]:
        workload_type = BURST

    opportunistic_cpus = 0
    if FENZO_WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY in passthrough_data:
        opportunistic_cpus = passthrough_data[FENZO_WORKLOAD_JSON_OPPORTUNISTIC_CPU_KEY]

    duration_predictions = []
    if WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY in passthrough_data:
        duration_predictions = get_duration_predictions(passthrough_data[WORKLOAD_JSON_RUNTIME_PREDICTIONS_KEY])

    return LegacyWorkload(
        launch_time=launch_time,
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
        opportunistic_thread_count=opportunistic_cpus,
        duration_predictions=duration_predictions)


def __get_workload_json(identifier):
    for attempt in range(WORKLOAD_JSON_READ_ATTEMPTS):
        try:
            with open(get_json_path(identifier)) as json_file:
                return json.load(json_file)
        except json.decoder.JSONDecodeError as err:
            log.debug("failed to read container %s json %s, retrying in %s seconds: %s", identifier,
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


def get_sorted_workloads(workloads: List[Workload]):
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
