import unittest

from tests.utils import TEST_POD_JOB_ID, TEST_POD_OWNER_EMAIL, get_simple_test_pod
from titus_isolate.event.constants import SERVICE
from titus_isolate.model.constants import JOB_DESCRIPTOR
from titus_isolate.model.kubernetes_workload import get_workload_from_pod
from titus_isolate.model.pod_utils import get_start_time, get_main_container, get_job_descriptor, decode_job_descriptor
from titus_isolate.monitor.utils import get_duration_predictions


class TestUtils(unittest.TestCase):

    def test_get_duration_predictions(self):
        input = "0.05=1.0;0.1=2.0;0.15=3.0;0.2=4.0;0.25=5.0;0.3=6.0;0.35=7.0;0.4=8.0;0.45=9.0;0.5=10.0;0.55=11.0;0.6=12.0;0.65=13.0;0.7=14.0;0.75=15.0;0.8=16.0;0.85=17.0;0.9=18.0;0.95=19.0"
        predictions = get_duration_predictions(input)
        self.assertEqual(19, len(predictions))

        percentile_step = 0.05
        duration_step = 1.0
        expected_percentile = 0
        expected_duration = 0

        for p in predictions:
            expected_percentile += percentile_step
            expected_duration += duration_step
            self.assertAlmostEqual(expected_percentile, p.get_percentile())
            self.assertAlmostEqual(expected_duration, p.get_duration())

    def test_empty_predictions_input(self):
        input = ""
        predictions = get_duration_predictions(input)
        self.assertEqual(0, len(predictions))

    def test_get_start_time(self):
        pod = get_simple_test_pod()
        self.assertEqual(1585004197000, get_start_time(pod))

        pod = get_simple_test_pod()
        pod.status.container_statuses = []
        self.assertEqual(None, get_start_time(pod))

        pod = get_simple_test_pod()
        pod.status.container_statuses[0].state = None
        self.assertEqual(None, get_start_time(pod))

        pod = get_simple_test_pod()
        pod.status.container_statuses[0].state.running = None
        self.assertEqual(None, get_start_time(pod))

    def test_get_main_container(self):
        pod = get_simple_test_pod()
        self.assertTrue(get_main_container(pod) is not None)

        pod = get_simple_test_pod()
        pod.spec.containers[0].name = 'not_the_pod_name'
        self.assertTrue(get_main_container(pod) is None)

        pod = get_simple_test_pod()
        pod.spec.containers = []
        self.assertTrue(get_main_container(pod) is None)

    def test_get_job_descriptor(self):
        pod = get_simple_test_pod()
        self.assertTrue(get_job_descriptor(pod) is not None)

        pod = get_simple_test_pod()
        pod.metadata = None
        self.assertTrue(get_job_descriptor(pod) is None)

        pod = get_simple_test_pod()
        pod.metadata.annotations = None
        self.assertTrue(get_job_descriptor(pod) is None)

        pod = get_simple_test_pod()
        del pod.metadata.annotations[JOB_DESCRIPTOR]
        self.assertTrue(get_job_descriptor(pod) is None)

    def test_decode_job_descriptor(self):
        pod = get_simple_test_pod()
        raw_jd = pod.metadata.annotations[JOB_DESCRIPTOR]
        self.assertTrue(decode_job_descriptor(raw_jd) is not None)

        raw_jd = "not_decodable_string"
        self.assertTrue(decode_job_descriptor(raw_jd) is None)

    def test_job_attrs_from_pod_v0(self):
        pod = get_simple_test_pod()
        w = get_workload_from_pod(pod)
        self.assertEqual(TEST_POD_JOB_ID, w.get_job_id())

    def test_job_attrs_from_pod_v1(self):
        pod = get_simple_test_pod(v1=True)
        w = get_workload_from_pod(pod)
        self.assertEqual(TEST_POD_JOB_ID, w.get_job_id())