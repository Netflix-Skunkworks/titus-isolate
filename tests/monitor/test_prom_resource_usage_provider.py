import unittest
from datetime import datetime, timedelta

from tests.config.test_property_provider import TestPropertyProvider
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.monitor.prom_resource_usage_provider import PrometheusResourceUsageProvider, dt2str
from titus_isolate.utils import set_config_manager

now = datetime.utcnow()
end = dt2str(now)
start = dt2str(now - timedelta(hours=1))


class TestPromResourceUsageProvider(unittest.TestCase):

    def test_get_cpu(self):
        set_config_manager(ConfigManager(TestPropertyProvider({
            'EC2_INSTANCE_ID': 'i-024e1158e6142b8c5'
        })))
        p = PrometheusResourceUsageProvider()
        usages = p._get_cpu([".*"], start, end)
        self.assertEqual(None, usages)
