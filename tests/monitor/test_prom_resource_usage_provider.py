import unittest
from datetime import datetime, timedelta

from titus_isolate.monitor.prom_resource_usage_provider import PrometheusResourceUsageProvider, dt2str

now = datetime.utcnow()
end = dt2str(now)
start = dt2str(now - timedelta(hours=1))


class TestPromResourceUsageProvider(unittest.TestCase):

    def test_get_cpu(self):
        p = PrometheusResourceUsageProvider()
        usages = p._get_cpu(start, end)
        self.assertEqual(None, usages)
