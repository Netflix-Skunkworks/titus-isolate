import abc
from abc import abstractmethod
from typing import List, Dict

from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload


class FreeThreadProvider(abc.ABC, MetricsReporter):

    @abstractmethod
    def get_free_threads(
            self,
            cpu: Cpu,
            workload_map: Dict[str, Workload],
            cpu_usage: Dict[str, float] = None) -> List[Thread]:
        pass
