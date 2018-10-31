import logging

from titus_isolate.docker.constants import ACTOR, ATTRIBUTES, NAME, CPU_LABEL_KEY, WORKLOAD_TYPE_LABEL_KEY, \
    REQUIRED_LABELS
from titus_isolate.model.workload import Workload

log = logging.getLogger()


def get_container_name(event):
    return event[ACTOR][ATTRIBUTES][NAME]


def get_cpu_count(create_event):
    return int(create_event[ACTOR][ATTRIBUTES][CPU_LABEL_KEY])


def get_workload_type(create_event):
    return create_event[ACTOR][ATTRIBUTES][WORKLOAD_TYPE_LABEL_KEY]


def get_current_workloads(docker_client):
    workloads = []
    for container in docker_client.containers.list():
        workload_id = container.name
        if __has_required_labels(container):
            try:
                cpu = int(container.labels[CPU_LABEL_KEY])
                workload_type = container.labels[WORKLOAD_TYPE_LABEL_KEY]
                workloads.append(Workload(workload_id, cpu, workload_type))
            except:
                log.exception("Failed to parse labels for container: '{}'".format(container.name))
        else:
            log.warning("Found running workload: '{}' without expected label: '{}'".format(workload_id, CPU_LABEL_KEY))

    return workloads


def __has_required_labels(container):
    for l in REQUIRED_LABELS:
        if l not in container.labels:
            return False

    return True
