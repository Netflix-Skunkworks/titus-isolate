from titus_isolate import log
from titus_isolate.event.constants import ACTOR, ATTRIBUTES, NAME, CPU_LABEL_KEY, WORKLOAD_TYPE_LABEL_KEY, \
    REQUIRED_LABELS, MEM_LABEL_KEY, DISK_LABEL_KEY, NETWORK_LABEL_KEY, IMAGE_LABEL_KEY
from titus_isolate.model.workload import Workload


def get_container_name(event):
    return event[ACTOR][ATTRIBUTES][NAME]


def get_cpu(create_event):
    return __get_int_attribute(create_event, CPU_LABEL_KEY)


def get_mem(create_event):
    return __get_int_attribute(create_event, MEM_LABEL_KEY)


def get_disk(create_event):
    return __get_int_attribute(create_event, DISK_LABEL_KEY)


def get_network(create_event):
    return __get_int_attribute(create_event, NETWORK_LABEL_KEY)


def __get_int_attribute(event, key):
    return int(event[ACTOR][ATTRIBUTES][key])


def get_image(create_event):
    return create_event[ACTOR][ATTRIBUTES][IMAGE_LABEL_KEY]


def get_workload_type(create_event):
    return create_event[ACTOR][ATTRIBUTES][WORKLOAD_TYPE_LABEL_KEY]


def get_current_workloads(docker_client):
    workloads = []
    for container in docker_client.containers.list():
        workload_id = container.name
        if __has_required_labels(container):
            try:
                cpu = int(container.labels[CPU_LABEL_KEY])
                mem = int(container.labels[MEM_LABEL_KEY])
                disk = int(container.labels[DISK_LABEL_KEY])
                network = int(container.labels[NETWORK_LABEL_KEY])
                image = container.labels[IMAGE_LABEL_KEY]
                workload_type = container.labels[WORKLOAD_TYPE_LABEL_KEY]
                workloads.append(Workload(workload_id, cpu, mem, disk, network, image, workload_type))
                log.info("Found running workload: '{}'".format(workload_id))
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
