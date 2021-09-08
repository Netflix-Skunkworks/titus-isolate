import datetime
import signal
from typing import List
import re

from titus_isolate import log
from titus_isolate.event.constants import ACTOR, ATTRIBUTES, NAME
from titus_isolate.model.utils import get_workload
from titus_isolate.model.workload_interface import Workload

epoch = datetime.datetime.utcfromtimestamp(0)

UUID_REGEX = r'^\b[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}$'


def get_container_name(event):
    return __get_attribute(event, NAME)


def __get_attribute(event, key, default=''):
    attributes = event[ACTOR][ATTRIBUTES]
    return __get_value(attributes, key, default)


def __get_value(dictionary, key, default=''):
    return dictionary.get(key, default)


def get_current_workloads(docker_client) -> List[Workload]:
    workloads = []
    signal.alarm(60)
    for container in docker_client.containers.list():
        if not container_looks_like_titus_task(container):
            continue
        workload = None
        try:
            workload = get_workload(container.name)
        except Exception:
            log.error("Failed to get workload: '%s'", container.name)

        if workload is not None:
            workloads.append(workload)

    signal.alarm(0)
    return workloads


def container_looks_like_titus_task(container) -> bool:
    """ All container that refer to titus tasks look like UUIDs.
    Any non-uuid are likely to be extraContainers (sidecars), or potentially
    other random junk. titus-isolate should not try to do
    anything with these containers that cannot be looked up
    in the titus api. """
    return bool(re.match(UUID_REGEX, container.name))


def is_event_from_a_titus_task(event) -> bool:
    name = get_container_name(event)
    return container_looks_like_titus_task(name)


def unix_time_millis(dt: datetime):
    return (dt - epoch).total_seconds() * 1000.0


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False
