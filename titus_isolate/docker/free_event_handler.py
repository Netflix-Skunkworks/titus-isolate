from titus_isolate.docker.constants import ACTION
from titus_isolate.docker.event_handler import EventHandler
from titus_isolate.docker.utils import get_container_name


class FreeEventHandler(EventHandler):
    FREE_ACTIONS = ["destroy", "die", "kill", "oom", "stop"]

    def __init__(self, resource_manager):
        super().__init__(resource_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        workload_id = get_container_name(event)
        freed_threads = self.resource_manager.free_threads(workload_id)
        freed_thread_ids = [t.get_id() for t in freed_threads]
        self.handled_event(event, "freed threads: '{}'  for workload: '{}'".format(freed_thread_ids, workload_id))

    def __relevant(self, event):
        action = event[ACTION].lower()
        self.ignored_event(event, "action: '{}' should not free cpu resources".format(action))
        return action in self.FREE_ACTIONS
