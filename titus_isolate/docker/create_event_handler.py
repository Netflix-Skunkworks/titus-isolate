import logging

from titus_isolate.docker.constants import ACTION, ACTOR, ATTRIBUTES, CPU_LABEL_KEY, CREATE, NAME
from titus_isolate.docker.event_handler import EventHandler
from titus_isolate.docker.utils import get_container_name, get_cpu_count
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
        workload = Workload(name, cpus)

        self.workload_manager.add_workloads([workload])
        self.handled_event(event, "added workload: '{}'".format(workload.get_id()))

    def __relevant(self, event):
        if not event[ACTION] == CREATE:
            self.ignored_event(event, "not a CREATE event")
            return False

        if CPU_LABEL_KEY not in event[ACTOR][ATTRIBUTES]:
            self.ignored_event(event, "container created without label: '{}'".format(CPU_LABEL_KEY))
            return False

        return True

