from titus_isolate.event.constants import ACTION, CONTAINER_BATCH, STARTS, DIES
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import get_container_name
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.metrics.constants import CONTAINER_BATCH_SIZE_KEY
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.utils import get_workload


class ContainerBatchEventHandler(EventHandler, MetricsReporter):

    def __init__(self, workload_manger: WorkloadManager):
        super().__init__()
        self.__reg = None
        self.__tags = None
        self.__workload_manager = workload_manger

    def handle(self, event):
        if not self.__relevant(event):
            return

        self.handling_event(event, "handling container event batch")

        start_events = event[STARTS]
        die_events = event[DIES]

        adds = []
        for start in start_events:
            container_name = get_container_name(start)
            if container_name is '':
                self.ignored_event(event, 'unable to get container name from start event')
                continue

            workload = get_workload(container_name)
            if workload is None:
                self.ignored_event(event, 'failed to construct workload from start event')
                continue

            adds.append(workload)

        removes = []
        for die in die_events:
            workload_id = get_container_name(die)
            removes.append(workload_id)

        self.__report_batch_size(len(adds + removes))
        self.__workload_manager.isolate(adds=adds, removes=removes)
        self.handled_event(event, "handled container event batch")

    def __relevant(self, event):
        if not event[ACTION] == CONTAINER_BATCH:
            self.ignored_event(event, "not a CONTAINER_BATCH event")
            return False

        return True

    def __report_batch_size(self, size: int):
        if self.__reg is not None:
            self.__reg.distribution_summary(CONTAINER_BATCH_SIZE_KEY, self.__tags).record(size)

    def set_registry(self, registry, tags):
        self.__reg = registry
        self.__tags = tags

    def report_metrics(self, tags):
        pass
