import copy

from titus_isolate.event.constants import ACTION, RECONCILE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.isolate.reconciler import Reconciler
from titus_isolate.utils import get_workload_manager


class ReconcileEventHandler(EventHandler):
    def __init__(self, reconciler: Reconciler):
        super().__init__(None)
        self.__reconciler = reconciler

    def handle(self, event):
        if not self.__relevant(event):
            return

        cpu = copy.deepcopy(get_workload_manager().get_cpu())
        self.handling_event(event, "reconciling titus-isolate and cgroup state")
        self.__reconciler.reconcile(cpu)
        self.handled_event(event, "reconciled titus-isolate and cgroup state")

    def __relevant(self, event):
        if not event[ACTION] == RECONCILE:
            self.ignored_event(event, "not a {} event".format(RECONCILE))
            return False

        return True
