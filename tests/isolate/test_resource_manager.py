import unittest

from tests.docker.mock_docker import MockDockerClient
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.model.processor.utils import get_cpu


class TestResourceManager(unittest.TestCase):
    def test_invalid_construction(self):
        with self.assertRaises(ValueError):
            ResourceManager(cpu=get_cpu(), docker_client=MockDockerClient(), dry_run=True)
