from titus_isolate.event.constants import ACTION
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import get_container_name


class FreeEventHandler(EventHandler):
    FREE_ACTIONS = ["die"]

    def __init__(self, workload_manager):
        super().__init__(workload_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        workload_id = get_container_name(event)
        self.handling_event(event, "removing workload: '{}'".format(workload_id))
        self.workload_manager.remove_workload(workload_id)
        self.handled_event(event, "removed workload: '{}'".format(workload_id))

    def __relevant(self, event):
        action = event[ACTION].lower()
        if action not in self.FREE_ACTIONS:
            self.ignored_event(event, "action: '{}' should not free cpu resources".format(action))
            return False

        return True
