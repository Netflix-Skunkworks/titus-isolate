from titus_isolate.event.constants import ACTION, REBALANCE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.isolate.workload_manager import WorkloadManager


class RebalanceEventHandler(EventHandler):

    def __init__(self, workload_manager: WorkloadManager):
        super().__init__()
        self.__workload_manager = workload_manager

    def handle(self, event):
        if not self.__relevant(event):
            return

        self.handling_event(event, "rebalancing workloads")
        self.__workload_manager.isolate(adds=[], removes=[])
        self.handled_event(event, "rebalanced workloads")

    def __relevant(self, event):
        if not event[ACTION] == REBALANCE:
            self.ignored_event(event, "not a {} event".format(REBALANCE))
            return False

        return True
