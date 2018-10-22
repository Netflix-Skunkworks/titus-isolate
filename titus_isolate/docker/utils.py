import logging

from titus_isolate.docker.constants import ACTOR, ATTRIBUTES, NAME, CPU_LABEL_KEY
from titus_isolate.model.workload import Workload

log = logging.getLogger()


def get_container_name(event):
    return event[ACTOR][ATTRIBUTES][NAME]


def get_cpu_count(create_event):
    return int(create_event[ACTOR][ATTRIBUTES][CPU_LABEL_KEY])


def get_current_workloads(docker_client):
    workloads = []
    for container in docker_client.containers.list():
        workload_id = container.name
        if CPU_LABEL_KEY in container.labels:
            cpu = int(container.labels[CPU_LABEL_KEY])
            workloads.append(Workload(workload_id, cpu))
        else:
            log.warning("Found running workload: '{}' without expected label: '{}'".format(workload_id, CPU_LABEL_KEY))

    return workloads
