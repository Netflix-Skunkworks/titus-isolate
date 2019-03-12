import os
from datetime import datetime as dt

import numpy as np

from titus_isolate import log
from titus_isolate.model.workload import Workload

from titus_optimize.data import Query, build_ts_features
from titus_optimize.predictors import PredictorWithFilter

class CpuUsagePredictor:

    def __init__(self, model_path, use_whitelist=True):
        pf = CpuUsagePredictor.__load_model_from_file(model_path)
        self.__use_whitelist = use_whitelist
        self.__model = pf
    
    def predict(self, workload : Workload, cpu_usage_last_hour : np.array) -> float:
        image = workload.get_image()
        # todo split
        if self.__use_whitelist and (image not in self.__model.filter):
            # not in whitelist, predict without context features
            q = Query(
                None, # user
                None, # app_name
                None, # num_cpu_requested TODO
                None, # ram_requested
                None, # disk_requested
                None, # network_requested
                None, # job_type
                None, # region
                None, # env
                None, # hour of day
                build_ts_features(cpu_usage_last_hour)
            )
        else:
            q = Query(
                None, # user
                None, # app_name
                workload.get_thread_count(),
                workload.get_mem(),
                workload.get_disk(),
                workload.get_network(),
                None, # job_type
                None, # region
                None, # env
                dt.utcnow().hour,
                build_ts_features(cpu_usage_last_hour)
            )

        return self.__model.ml_model.predict_single(q)
    
    @staticmethod
    def __load_model_from_file(path):
        if not os.path.isfile(path):
            raise Exception("Could not find a model at `%s`" % (path,))
        model =  PredictorWithFilter.load(open(path, "rb").read())
        log.info("Loaded CPU usage predictor. Meta-data: %s. Whitelist size: %s" % (model.meta_data, len(model.filter)))
        return model
