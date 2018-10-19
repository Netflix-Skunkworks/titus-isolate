import logging

from titus_isolate.docker.constants import ACTION, ACTOR, ATTRIBUTES, CPU_LABEL_KEY, CREATE, NAME
from titus_isolate.docker.event_handler import EventHandler
from titus_isolate.docker.utils import get_container_name, get_cpu_count
from titus_isolate.model.workload import Workload

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


class CreateEventHandler(EventHandler):
    def __init__(self, resource_manager):
        super().__init__(resource_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        name = get_container_name(event)
        cpus = get_cpu_count(event)
        workload = Workload(name, cpus)

        assigned_threads = self.resource_manager.assign_threads(workload)
        assigned_thread_ids = [t.get_id() for t in assigned_threads]
        self.handled_event(
            event,
            "assigned threads: '{}' to workload: '{}'".format(assigned_thread_ids, workload.get_id()))

    def __relevant(self, event):
        if not event[ACTION] == CREATE:
            self.ignored_event(event, "not a CREATE event")
            return False

        if CPU_LABEL_KEY not in event[ACTOR][ATTRIBUTES]:
            self.ignored_event(event, "container created without label: '{}'".format(CPU_LABEL_KEY))
            return False

        return True

