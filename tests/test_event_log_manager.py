from titus_isolate import log
from titus_isolate.metrics.event_log_manager import EventLogManager
from titus_isolate.model.processor.cpu import Cpu


class TestEventLogManager(EventLogManager):
    def report_cpu(self, cpu: Cpu, workloads: list):
        log.info("Mock reporting cpu: {}, workloads: {}".format(cpu, workloads))

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
