from abc import abstractmethod
from threading import Lock
from typing import Optional

import schedule

from titus_isolate import log
from titus_isolate.allocate.utils import download_latest_cpu_model, get_cpu_model_file_path, CPU_PREDICTOR, \
    DEFAULT_CPU_PREDICTOR, SERVICE_CPU_PREDICTOR, LEGACY_CPU_PREDICTOR
from titus_isolate.predict.resource_usage_predictor import ResourceUsagePredictor
from titus_isolate.predict.simple_cpu_predictor import SimpleCpuPredictor
from titus_isolate.utils import get_config_manager


class CpuUsagePredictorManager:

    @abstractmethod
    def get_cpu_predictor(self) -> Optional[SimpleCpuPredictor]:
        pass


class ConfigurableCpuUsagePredictorManager(CpuUsagePredictorManager):

    def __init__(self):
        self.__lock = Lock()
        self.__resource_usage_predictor = ResourceUsagePredictor()
        self.__cpu_usage_predictor = None

        self.__update_local_model()
        schedule.every(1).hour.do(self.__update_local_model)

    def __update_local_model(self):
        cpu_predictor = get_config_manager().get_str(CPU_PREDICTOR, DEFAULT_CPU_PREDICTOR)
        if cpu_predictor == LEGACY_CPU_PREDICTOR:
            raise Exception("Unsupported legacy CPU predictor")
        else:
            log.info("Skipping model update.  CPU predictor: %s", cpu_predictor)

    def get_cpu_predictor(self) -> Optional[SimpleCpuPredictor]:
        config_manager = get_config_manager()
        cpu_predictor = config_manager.get_str(CPU_PREDICTOR, DEFAULT_CPU_PREDICTOR)
        log.info("Using cpu predictor: %s", cpu_predictor)

        if cpu_predictor == SERVICE_CPU_PREDICTOR:
            return self.__resource_usage_predictor

        if cpu_predictor == LEGACY_CPU_PREDICTOR:
            with self.__lock:
                return self.__cpu_usage_predictor

        return None
