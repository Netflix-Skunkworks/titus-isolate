import os
import re

import numpy as np

from titus_isolate import log
from titus_isolate.model.workload import Workload

from titus_optimize.data import Query2, build_ts_features
from titus_optimize.predictors import PredictorWithFilter


class PredEnvironment:
    def __init__(self, region, nflx_env, hour_of_day):
        self.region = region
        self.nflx_env = nflx_env
        self.hour_of_day = hour_of_day


class CpuUsagePredictor:

    def __init__(self, model_path, use_whitelist=True):
        pf = CpuUsagePredictor.__load_model_from_file(model_path)
        self.__use_whitelist = use_whitelist
        self.__model = pf
        self._img_name_regex = re.compile(r'^.+\:\d+/(.*)')
    
    def predict(self, workload: Workload, cpu_usage_last_hour: np.array, pred_env: PredEnvironment) -> float:
        image = workload.get_image()
        tokens = image.split('@')
        valid_digest = False
        if cpu_usage_last_hour is None:
            cpu_usage_last_hour = np.full((60,), np.nan, dtype=np.float32)
        image_name = None
        if len(tokens) == 2 and tokens[-1].startswith("sha256:"):
            m = self._img_name_regex.search(tokens[0])
            if m is not None:
                valid_digest = True
                image_name = m.groups(0)[0]
                entry_point = workload.get_entrypoint()[:1000]
                if entry_point is None:
                    entry_point = ""
                filter_key = "%s@%s" % (tokens[-1], entry_point)
        if self.__use_whitelist and valid_digest and (filter_key not in self.__model.filter):
            # not in whitelist, predict without context features
            q = Query2(
                None, # image_name
                None, # user
                None, # app_name
                workload.get_thread_count(),
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
            q = Query2(
                image_name,
                workload.get_owner_email(),
                workload.get_app_name(),
                workload.get_thread_count(),
                workload.get_mem(),
                workload.get_disk(),
                workload.get_network(),
                workload.get_job_type().lower(),
                pred_env.region,
                pred_env.nflx_env,
                pred_env.hour_of_day,
                build_ts_features(cpu_usage_last_hour)
            )

        return min(self.__model.ml_model.predict_single(q), workload.get_thread_count())
    
    def get_model(self):
        return self.__model

    @staticmethod
    def __load_model_from_file(path):
        if not os.path.isfile(path):
            raise Exception("Could not find a model at `%s`" % (path,))
        model =  PredictorWithFilter.load(open(path, "rb").read())
        log.info("Loaded CPU usage predictor. Meta-data: %s. Whitelist size: %s" % (model.meta_data, len(model.filter)))
        return model
