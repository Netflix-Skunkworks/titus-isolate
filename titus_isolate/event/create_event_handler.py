from titus_isolate.event.constants import ACTION, ACTOR, ATTRIBUTES, REQUIRED_LABELS, START
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import get_container_name
from titus_isolate.model.utils import get_workload_from_kubernetes, get_workload_from_disk
from titus_isolate.utils import is_kubernetes


class CreateEventHandler(EventHandler):
    def __init__(self, workload_manager):
        super().__init__(workload_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        workload = None
        container_name = get_container_name(event)

        if is_kubernetes():
            workload = get_workload_from_kubernetes(container_name)
        else:
            workload = get_workload_from_disk(container_name)

        if workload is None:
            raise Exception('failed to construct workload from event')

        self.handling_event(event, "adding workload: '{}'".format(workload.get_id()))
        self.workload_manager.add_workload(workload)
        self.handled_event(event, "added workload: '{}'".format(workload.get_id()))

    def __relevant(self, event):
        if not event[ACTION] == START:
            self.ignored_event(event, "not a START event")
            return False

        for expected_label in REQUIRED_LABELS:
            if expected_label not in event[ACTOR][ATTRIBUTES]:
                self.ignored_event(event, "container created without expected label: '{}'".format(expected_label))
                return False

        return True
