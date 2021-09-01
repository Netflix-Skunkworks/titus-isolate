from titus_isolate.event.constants import ACTION, ACTOR, ATTRIBUTES, REQUIRED_LABELS, START
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import get_container_name
from titus_isolate import log
from titus_isolate.model.utils import get_workload


class CreateEventHandler(EventHandler):
    def __init__(self, workload_manager):
        super().__init__()
        self.__workload_manager = workload_manager

    def handle(self, event):
        if not self.__relevant(event):
            return

        container_name = get_container_name(event)
        workload = get_workload(container_name)

        if workload is None:
            msg = 'failed to construct workload from event'
            log.error(msg)
            raise Exception(msg)

        self.handling_event(event, "adding workload: '{}'".format(workload.get_task_id()))
        self.__workload_manager.add_workload(workload)
        self.handled_event(event, "added workload: '{}'".format(workload.get_task_id()))

    def __relevant(self, event):
        if not event[ACTION] == START:
            self.ignored_event(event, "not a START event")
            return False

        for expected_label in REQUIRED_LABELS:
            if expected_label not in event[ACTOR][ATTRIBUTES]:
                self.ignored_event(event, "container created without expected label: '{}'".format(expected_label))
                return False

        return True
