from titus_isolate.docker.constants import ACTOR, ATTRIBUTES, NAME, CPU_LABEL_KEY


def get_container_name(event):
    return event[ACTOR][ATTRIBUTES][NAME]


def get_cpu_count(create_event):
    return int(create_event[ACTOR][ATTRIBUTES][CPU_LABEL_KEY])
