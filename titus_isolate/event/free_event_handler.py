from titus_isolate.event.constants import ACTION, DIE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import get_container_name
from titus_isolate.isolate.workload_manager import WorkloadManager


class FreeEventHandler(EventHandler):
    FREE_ACTIONS = [DIE]

    def __init__(self, workload_manager: WorkloadManager):
        super().__init__()
        self.__workload_manager = workload_manager

    def handle(self, event):
        if not self.__relevant(event):
            return

        workload_id = get_container_name(event)
        self.handling_event(event, "removing workload: '{}'".format(workload_id))
        self.__workload_manager.isolate(
            adds=[],
            removes=[workload_id])
        self.handled_event(event, "removed workload: '{}'".format(workload_id))

    def __relevant(self, event):
        action = event[ACTION].lower()
        if action not in self.FREE_ACTIONS:
            self.ignored_event(event, "action: '{}' should not free cpu resources".format(action))
            return False

        return True
