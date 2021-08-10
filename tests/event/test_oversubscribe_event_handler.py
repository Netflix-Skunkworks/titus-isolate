from typing import List, Optional, Dict

from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.resource_usage import GlobalResourceUsage
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager
from titus_isolate.predict.simple_cpu_predictor import SimpleCpuPredictor


class TestWorkloadManager:
    def __init__(self, workloads: List[Workload]):
        self.workloads = workloads

    def get_workloads(self) -> List[Workload]:
        return self.workloads


class TestSimpleCpuPredictor(SimpleCpuPredictor):

    def __init__(self, predictions: Dict[str, float]):
        self.predictions = predictions

    def get_cpu_predictions(self, workloads: List[Workload], resource_usage: GlobalResourceUsage) -> Optional[
        Dict[str, float]]:
        return self.predictions


class TestCpuUsagePredictorManager(CpuUsagePredictorManager):

    def __init__(self, predictor: SimpleCpuPredictor):
        self.predictor = predictor

    def get_cpu_predictor(self) -> Optional[SimpleCpuPredictor]:
        return self.predictor
