from titus_isolate.event.constants import ACTION, REBALANCE
from titus_isolate.event.event_handler import EventHandler


class RebalanceEventHandler(EventHandler):

    def __init__(self, workload_manager):
        super().__init__(workload_manager)

    def handle(self, event):
        if not self.__relevant(event):
            return

        self.handling_event(event, "rebalancing workloads")
        self.workload_manager.rebalance()
        self.handled_event(event, "rebalanced workloads")

    def __relevant(self, event):
        if not event[ACTION] == REBALANCE:
            self.ignored_event(event, "not a {} event".format(REBALANCE))
            return False

        return True
