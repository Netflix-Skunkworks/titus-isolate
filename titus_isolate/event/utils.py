import datetime

from titus_isolate import log
from titus_isolate.event.constants import ACTOR, ATTRIBUTES, NAME
from titus_isolate.model.utils import get_workload_from_disk, get_workload_from_kubernetes
from titus_isolate.utils import is_kubernetes

epoch = datetime.datetime.utcfromtimestamp(0)


def get_container_name(event):
    return __get_attribute(event, NAME)


def __get_attribute(event, key, default=''):
    attributes = event[ACTOR][ATTRIBUTES]
    return __get_value(attributes, key, default)


def __get_value(dictionary, key, default=''):
    return dictionary.get(key, default)


def get_current_workloads(docker_client):
    workloads = []
    for container in docker_client.containers.list():
        try:
            if is_kubernetes():
                workloads.append(get_workload_from_kubernetes(container.name))
            else:
                workloads.append(get_workload_from_disk(container.name))
        except:
            log.exception("Failed to read environment for container: '%s'", container.name)

    return workloads


def unix_time_millis(dt: datetime):
    return (dt - epoch).total_seconds() * 1000.0


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False
