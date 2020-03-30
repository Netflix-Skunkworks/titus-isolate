from typing import List

MODEL_VERSION = 'model_version'
MODEL_INSTANCE_ID = 'model_instance_id'
PREDICTION_TS_MS = 'prediction_ts_ms'
PREDICTIONS = 'predictions'
JOB_ID = 'job_id'
CPU = "cpu"
MEM_MB = "memMB"
NET_TRANS_MBPS = "net_transMbps"
NET_RECV_MBPS = 'net_recvMbps'
META_DATA = 'meta_data'
QUANTILE = 'quantile'
HORIZON_MINUTES = 'horizon_minutes'
PREDS = 'preds'

RESOURCE_KEYS = [
    CPU,
    MEM_MB,
    NET_TRANS_MBPS,
    NET_RECV_MBPS
]


# Example input
#
# {
#     'model_version': '0.1',
#     'model_instance_id': 'af66ac6b-feaa-4e90-877e-6b3c910f175a',
#     'prediction_ts_ms': '1584979201000',
#     'predictions': [{
#         'job_id': '8505c545-1824-40dd-963d-aacc54a8502e',
#         'cpu': [{
#             'quantile': 'p50',
#             'horizon_minutes': ['0-10', '10-30', '30-60', '60-360'],
#             'preds': [0.693147, 0.693147, 0.693147, 0.693147]
#         }, {
#             'quantile': 'p95',
#             'horizon_minutes': ['0-10', '10-30', '30-60', '60-360'],
#             'preds': [0.71392, 0.713309, 0.713462, 0.712815]
#         }],
#         'memMB': None,
#         'net_transMbps': None,
#         'net_recvMbps': None
#     }],
#     'meta_data': None
# }


class ResourceTypeUsagePrediction:
    def __init__(self, raw_predictions: List[dict]):
        self.horizons = {}
        self.predictions = {}

        if raw_predictions is not None:
            for p in raw_predictions:
                quantile = p[QUANTILE]
                self.horizons[quantile] = p[HORIZON_MINUTES]
                self.predictions[quantile] = p[PREDS]


class ResourceUsagePrediction:

    def __init__(self, raw_predictions: dict):
        self.resource_type_predictions = {}
        for k, v in raw_predictions.items():
            if k in RESOURCE_KEYS:
                self.resource_type_predictions[k] = ResourceTypeUsagePrediction(v)


class ResourceUsagePredictions:

    def __init__(self, raw: dict):
        self.raw = raw
        self.model_version = raw.get(MODEL_VERSION, "UNKNOWN_MODEL_VERSION")
        self.model_instance_id = raw.get(MODEL_INSTANCE_ID, "UNKNOWN_MODEL_INSTANCE_ID")
        self.prediction_ts_ms = int(raw.get(PREDICTION_TS_MS, '0'))
        self.metadata = raw.get(META_DATA, {})

        self.predictions = {}
        for p in raw.get(PREDICTIONS, {}):
            job_id = p.get(JOB_ID, "UNKNOWN_JOB_ID")
            self.predictions[job_id] = ResourceUsagePrediction(p)
