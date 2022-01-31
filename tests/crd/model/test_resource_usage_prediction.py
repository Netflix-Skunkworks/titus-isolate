import unittest
import uuid

from titus_isolate.crd.model.resource_usage_prediction import ResourceUsagePredictions

test_task_id = str(uuid.uuid4())
test_job_id = str(uuid.uuid4())
test_raw_prediction = {
    'model_version': '0.2',
    'model_instance_id': '523d600d-c83b-4e53-9a63-97e6257b8c89',
    'prediction_ts_ms': '1593199215000',
    'predictions': [{
        'task_id': test_task_id,
        'job_id': test_job_id,
        'cpu': [{
            'quantile': 'p50',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [0.0723083, 0.27779, 0.0404529, 0.0756278, 0.0390612]
        }, {
            'quantile': 'p95',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [0.100213, 0.318321, 0.0765069, 0.155187, 0.0640625]
        }],
        'memMB': [{
            'quantile': 'p50',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [394.013, 512, 512, 225.233, 38.1488]
        }, {
            'quantile': 'p95',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [512, 512, 512, 512, 408.21]
        }],
        'net_transMbps': [{
            'quantile': 'p50',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [0.256417, 0.291996, 0.275529, 0.322974, 0.298316]
        }, {
            'quantile': 'p95',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [0.514291, 0.591106, 0.551627, 0.594022, 0.587473]
        }],
        'net_recvMbps': [{
            'quantile': 'p50',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [0.277189, 0.294268, 0.243385, 0.270051, 0.470993]
        }, {
            'quantile': 'p95',
            'horizon_minutes': ['0-10', '10-30', '30-60', '60-360', '360-720'],
            'preds': [0.537605, 0.527281, 0.366524, 0.526459, 0.925797]
        }]
    }],
    'meta_data': None
}


class TestResourceUsagePrediction(unittest.TestCase):

    def test_add_resource_usage_predictions(self):
        preds = ResourceUsagePredictions(test_raw_prediction)
        first_job_prediction = preds.predictions[test_job_id]

        summed_job_prediction = first_job_prediction.add(first_job_prediction)
        for res_type, prediction in first_job_prediction.resource_type_predictions.items():
            for percentile in prediction.predictions.keys():
                for i in range(len(prediction.predictions[percentile])):
                    orig_pred = prediction.predictions[percentile][i]
                    summed_pred = summed_job_prediction.resource_type_predictions[res_type].predictions[percentile][i]
                    expected_doubled_pred = 2 * orig_pred
