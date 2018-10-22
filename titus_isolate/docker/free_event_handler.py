from titus_isolate.docker.constants import ACTION
from titus_isolate.docker.event_handler import EventHandler
from titus_isolate.docker.utils import get_container_name


class FreeEventHandler(EventHandler):
    FREE_ACTIONS = ["destroy", "die", "kill", "oom", "stop"]

    def __init__(self, workload_manager):
        super().__init__(workload_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        workload_id = get_container_name(event)
        self.workload_manager.remove_workloads([workload_id])
        self.handled_event(event, "removed workload: '{}'".format(workload_id))

    def __relevant(self, event):
        action = event[ACTION].lower()
        self.ignored_event(event, "action: '{}' should not free cpu resources".format(action))
        return action in self.FREE_ACTIONS
