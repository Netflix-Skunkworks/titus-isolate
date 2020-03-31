from abc import abstractmethod
from typing import List, Dict, Optional

from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.resource_usage import GlobalResourceUsage


class SimpleCpuPredictor:

    @abstractmethod
    def get_cpu_predictions(self, workloads: List[Workload], resource_usage: GlobalResourceUsage) \
            -> Optional[Dict[str, float]]:
        pass
