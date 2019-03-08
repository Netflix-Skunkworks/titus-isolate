from titus_isolate.event.constants import ACTION, ACTOR, ATTRIBUTES, CREATE, REQUIRED_LABELS
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.model.utils import get_workload_from_event


class CreateEventHandler(EventHandler):
    def __init__(self, workload_manager):
        super().__init__(workload_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        workload = get_workload_from_event(event)

        self.handling_event(event, "adding workload: '{}'".format(workload.get_id()))
        self.workload_manager.add_workload(workload)
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
