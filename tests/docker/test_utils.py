import unittest

from tests.docker.mock_docker import MockDockerClient, MockContainer
from titus_isolate.docker.constants import STATIC
from titus_isolate.docker.utils import get_current_workloads
from titus_isolate.model.workload import Workload


class TestUtils(unittest.TestCase):
    def test_get_current_workloads(self):
        docker_client = MockDockerClient()
        self.assertEqual(0, len(get_current_workloads(docker_client)))

        c0_name = "c0"
        c0_thread_count = 1
        docker_client.add_container(self.__get_test_container(c0_name, c0_thread_count))

        c1_name = "c1"
        c1_thread_count = 2
        docker_client.add_container(self.__get_test_container(c1_name, c1_thread_count))

        current_workloads = get_current_workloads(docker_client)
        self.assertEqual(2, len(current_workloads))

        workload0 = get_current_workloads(docker_client)[0]
        self.assertEqual(c0_name, workload0.get_id())
        self.assertEqual(c0_thread_count, workload0.get_thread_count())

        workload1 = get_current_workloads(docker_client)[1]
        self.assertEqual(c1_name, workload1.get_id())
        self.assertEqual(c1_thread_count, workload1.get_thread_count())

    @staticmethod
    def __get_test_container(name, thread_count):
        return MockContainer(Workload(name, thread_count, STATIC))
