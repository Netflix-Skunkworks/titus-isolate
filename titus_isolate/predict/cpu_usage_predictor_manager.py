from threading import Lock

import schedule

from titus_isolate.allocate.utils import download_latest_cpu_model, get_cpu_model_file_path
from titus_isolate.predict.cpu_usage_predictor import CpuUsagePredictor


class CpuUsagePredictorManager:

    def __init__(self):
        self.__lock = Lock()
        self.__predictor = None

        self.__update_predictor()
        schedule.every(1).hour.do(self.__update_predictor)

    def __update_predictor(self):
        download_latest_cpu_model()
        with self.__lock:
            self.__predictor = CpuUsagePredictor(get_cpu_model_file_path())

    def get_predictor(self):
        with self.__lock:
            return self.__predictor
