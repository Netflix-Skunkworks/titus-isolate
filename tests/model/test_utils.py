import unittest

from titus_isolate.model.utils import get_duration_predictions


class TestWorkload(unittest.TestCase):

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
