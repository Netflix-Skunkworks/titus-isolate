import logging

from titus_isolate.docker.constants import ACTION, ACTOR, ATTRIBUTES, CREATE, REQUIRED_LABELS
from titus_isolate.docker.event_handler import EventHandler
from titus_isolate.docker.utils import get_container_name, get_cpu_count, get_workload_type
from titus_isolate.model.workload import Workload

log = logging.getLogger()


class CreateEventHandler(EventHandler):
    def __init__(self, workload_manager):
        super().__init__(workload_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        name = get_container_name(event)
        cpus = get_cpu_count(event)
        workload_type = get_workload_type(event)

        workload = Workload(name, cpus, workload_type)

        self.workload_manager.add_workloads([workload])
        self.handled_event(event, "added workload: '{}'".format(workload.get_id()))

    def __relevant(self, event):
        if not event[ACTION] == CREATE:
            self.ignored_event(event, "not a CREATE event")
            return False

        for expected_label in REQUIRED_LABELS:
            if expected_label not in event[ACTOR][ATTRIBUTES]:
                self.ignored_event(event, "container created without expected label: '{}'".format(expected_label))
                return False

        return True

