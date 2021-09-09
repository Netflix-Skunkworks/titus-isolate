import datetime
import signal
from typing import List

from titus_isolate import log
from titus_isolate.event.constants import ACTOR, ATTRIBUTES, NAME, TASK_ID
from titus_isolate.model.utils import get_workload
from titus_isolate.model.workload_interface import Workload

epoch = datetime.datetime.utcfromtimestamp(0)


def get_container_name(event):
    return __get_attribute(event, NAME)


def get_task_id(event):
    return __get_attribute(event, TASK_ID)


def __get_attribute(event, key, default=''):
    attributes = event[ACTOR][ATTRIBUTES]
    return __get_value(attributes, key, default)


def __get_value(dictionary, key, default=''):
    return dictionary.get(key, default)


def get_current_workloads(docker_client) -> List[Workload]:
    workloads = []
    signal.alarm(60)
    for container in docker_client.containers.list():
        workload = None
        try:
            workload = get_workload(container.name)
        except Exception:
            log.error("Failed to get workload: '%s'", container.name)

        if workload is not None:
            workloads.append(workload)

    signal.alarm(0)
    return workloads


def unix_time_millis(dt: datetime):
    return (dt - epoch).total_seconds() * 1000.0


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False
