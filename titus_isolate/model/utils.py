import json
import re
import time

from typing import List, Optional

from titus_isolate import log
from titus_isolate.cgroup.utils import get_json_path, get_env_path
from titus_isolate.config.constants import GET_WORKLOAD_RETRY_COUNT, DEFAULT_GET_WORKLOAD_RETRY_COUNT, \
    GET_WORKLOAD_RETRY_INTERVAL_SEC, DEFAULT_GET_WORKLOAD_RETRY_INTERVAL_SEC
from titus_isolate.model.constants import *
from titus_isolate.model.kubernetes_workload import KubernetesWorkload
from titus_isolate.model.workload_interface import Workload
from titus_isolate.utils import get_pod_manager, managers_are_initialized, get_config_manager


def get_duration(workload: Workload, percentile: float) -> Optional[float]:
    for p in workload.get_duration_predictions():
        if p.get_percentile() == percentile:
            return p.get_duration()

    return None


def get_workload(identifier) -> Optional[KubernetesWorkload]:
    if not managers_are_initialized():
        log.error("Cannot get workload from kubernetes because managers aren't initialized")
        return None

    retry_count = get_config_manager().get_int(GET_WORKLOAD_RETRY_COUNT, DEFAULT_GET_WORKLOAD_RETRY_COUNT)
    retry_interval = get_config_manager().get_float(GET_WORKLOAD_RETRY_INTERVAL_SEC, DEFAULT_GET_WORKLOAD_RETRY_INTERVAL_SEC)

    pod_manager = get_pod_manager()
    for i in range(retry_count):
        log.info("Getting pod from kubernetes: %s", identifier)
        pod = pod_manager.get_pod(identifier)
        if pod is not None:
            log.info("Got pod from kubernetes: %s", identifier)
            try:
                return KubernetesWorkload(pod)
            except Exception as e:
                log.exception("failed to construct kubernetes workload because: %s", e)
                return None

        log.info("Retrying getting pod from kubernetes in %s seconds", retry_interval)
        time.sleep(retry_interval)

    log.error("Failed to get pod from kubernetes: %s", identifier)
    return None


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


def release_all_threads(cpu, workloads):
    for w in workloads:
        release_threads(cpu, w.get_id())


def release_threads(cpu, workload_id):
    for t in cpu.get_threads():
        t.free(workload_id)
