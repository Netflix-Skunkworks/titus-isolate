import copy
from pprint import pformat
from typing import List

from six import iteritems

from .resources_capacity import ResourcesCapacity
from ...model.constants import PREDICTED_USAGE_RESOURCE_API_VERSION

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

PREDICTED_RESOURCE_USAGE_KIND = 'PredictedResourceUsage'
PREDICTED_RESOURCE_USAGE_NAMESPACE = 'default'
PREDICTED_RESOURCE_USAGE_NODE_NAME_LABEL_KEY = 'node_name'
PREDICTED_RESOURCE_USAGE_NODE_UID_LABEL_KEY = 'node_uid'
PREDICTED_RESOURCE_USAGE_PLURAL = 'resource-usage-predictions'

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
    openapi_types = {
        'horizon_minutes': 'dict(str, list[str])',
        'predictions': 'dict(str, list[float])'
    }

    attribute_map = {
        'horizon_minutes': 'horizonMinutes',
        'predictions': 'predictions'
    }

    def __init__(self, raw_predictions: List[dict]):
        self.__horizons = {}
        self.__predictions = {}

        if raw_predictions is not None:
            for p in raw_predictions:
                quantile = p[QUANTILE]
                self.__horizons[quantile] = p[HORIZON_MINUTES]
                self.__predictions[quantile] = p[PREDS]

    @property
    def horizon_minutes(self):
        return self.__horizons

    @horizon_minutes.setter
    def horizon_minutes(self, horizon_minutes):
        self.__horizons = horizon_minutes

    @property
    def predictions(self):
        return self.__predictions

    @predictions.setter
    def predictions(self, preds):
        self.__predictions = preds

    def add(self, other):
        out = copy.deepcopy(self)

        if other is None:
            return out

        for percentile, predictions in out.predictions.items():
            for i in range(len(predictions)):
                out.predictions[percentile][i] += other.predictions[percentile][i]

        return out


class ResourceUsagePrediction:
    openapi_types = {
        'resource_type_predictions': 'dict(str, ResourceTypeUsagePrediction)',
    }

    attribute_map = {
        'resource_type_predictions': 'typePredictions',
    }

    def __init__(self, raw_predictions: dict):
        self.__resource_type_predictions = {}
        for k, v in raw_predictions.items():
            if k in RESOURCE_KEYS:
                self.__resource_type_predictions[k] = ResourceTypeUsagePrediction(v)

    @property
    def resource_type_predictions(self):
        return self.__resource_type_predictions

    @resource_type_predictions.setter
    def resource_type_predictions(self, resource_type_predictions):
        self.__resource_type_predictions = resource_type_predictions

    def add(self, other):
        out = copy.deepcopy(self)

        if other is None:
            return out

        for res_type, predictions in out.resource_type_predictions.items():
            out.resource_type_predictions[res_type] = \
                out.resource_type_predictions[res_type].add(other.resource_type_predictions[res_type])

        return out


class ResourceUsagePredictions:
    openapi_types = {
        'predictions': 'dict(str, ResourceUsagePrediction)',
    }

    attribute_map = {
        'predictions': 'predictions',
    }

    def __init__(self, raw: dict):
        self.raw = raw
        self.model_version = raw.get(MODEL_VERSION, "UNKNOWN_MODEL_VERSION")
        self.model_instance_id = raw.get(MODEL_INSTANCE_ID, "UNKNOWN_MODEL_INSTANCE_ID")
        self.prediction_ts_ms = int(raw.get(PREDICTION_TS_MS, '0'))
        self.metadata = raw.get(META_DATA, {})
        self.__predictions = {}

        preds = raw.get(PREDICTIONS)
        if preds is not None:
            for p in preds:
                job_id = p.get(JOB_ID, "UNKNOWN_JOB_ID")
                self.__predictions[job_id] = ResourceUsagePrediction(p)

    @property
    def predictions(self):
        return self.__predictions

    @predictions.setter
    def predictions(self, predictions):
        self.__predictions = predictions

    def set_prediction_ts_ms(self, prediction_ts_ms : int):
        self.prediction_ts_ms = prediction_ts_ms


class CondensedResourceUsagePrediction:
    openapi_types = {
        'prediction': 'ResourceUsagePrediction',
        'model_version': 'str',
        'model_instance_id': 'str',
        'prediction_ts_ms': 'int',
        'resources_capacity': 'dict(str,int)',
        'metadata': 'dict(str, str)'
    }

    attribute_map = {
        'prediction': 'prediction',
        'model_version': 'model_version',
        'model_instance_id': 'model_instance_id',
        'prediction_ts_ms': 'prediction_ts_ms',
        'resources_capacity': 'resources_capacity',
        'metadata': 'metadata'
    }

    def __init__(self, resource_usage_predictions: ResourceUsagePredictions, resources_capacity: ResourcesCapacity):
        self.__prediction = self.__condense_predictions(list(resource_usage_predictions.predictions.values()))
        self.__resource_usage_predictions = resource_usage_predictions
        self.__resources_capacity = resources_capacity

    @property
    def prediction(self):
        return self.__prediction

    @property
    def model_version(self):
        return self.__resource_usage_predictions.model_version

    @property
    def model_instance_id(self):
        return self.__resource_usage_predictions.model_instance_id

    @property
    def prediction_ts_ms(self):
        return self.__resource_usage_predictions.prediction_ts_ms

    @property
    def resources_capacity(self):
        return self.__resources_capacity.to_dict()

    @property
    def metadata(self):
        return self.__resource_usage_predictions.metadata

    @staticmethod
    def __condense_predictions(predictions: List[ResourceUsagePrediction]) -> ResourceUsagePrediction:
        if len(predictions) < 1:
            return ResourceUsagePrediction({})

        out = predictions[0]
        for i in range(1, len(predictions)):
            out = out.add(predictions[i])

        return out


class ResourceUsagePredictionsResource:

    openapi_types = {
        'api_version': 'str',
        'kind': 'str',
        'metadata': 'V1ObjectMeta',
        'spec': 'CondensedResourceUsagePrediction'
    }

    attribute_map = {
        'api_version': 'apiVersion',
        'kind': 'kind',
        'metadata': 'metadata',
        'spec': 'spec'
    }

    def __init__(self,
                 api_version=PREDICTED_USAGE_RESOURCE_API_VERSION,
                 kind=PREDICTED_RESOURCE_USAGE_KIND,
                 metadata=None,
                 spec=None):

        self._api_version = api_version
        self._kind = kind
        self._metadata = metadata
        self._spec = spec

    @property
    def api_version(self):
        return self._api_version

    @api_version.setter
    def api_version(self, api_version):
        self._api_version = api_version

    @property
    def kind(self):
        return self._kind

    @kind.setter
    def kind(self, kind):
        self._kind = kind

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, metadata):
        self._metadata = metadata

    @property
    def spec(self):
        return self._spec

    @spec.setter
    def spec(self, spec):
        if spec is None:
            raise ValueError("Invalid value for `spec`, must not be `None`")
        self._spec = spec

    def to_dict(self):
        result = {}

        for attr, _ in iteritems(self.openapi_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value

        return result

    def to_str(self):
        return pformat(self.to_dict())

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        if not isinstance(other, ResourceUsagePredictionsResource):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
