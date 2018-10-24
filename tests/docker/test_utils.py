import logging
import unittest

from tests.docker.mock_docker import MockDockerClient, MockContainer
from titus_isolate.docker.constants import STATIC, CPU_LABEL_KEY
from titus_isolate.docker.utils import get_current_workloads
from titus_isolate.model.workload import Workload
from titus_isolate.utils import config_logs

config_logs(logging.DEBUG)
log = logging.getLogger()


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

    def test_get_current_malformed_workloads(self):
        # The BadContainer is missing an expected label
        class BadContainer:
            def __init__(self):
                self.name = "bad-container"
                self.labels = {
                    CPU_LABEL_KEY: 2,
                }
                self.update_calls = []

            def update(self, **kwargs):
                log.info("bad container update called with: '{}'".format(kwargs))
                threads = kwargs["cpuset_cpus"].split(',')
                self.update_calls.append(threads)

        docker_client = MockDockerClient()
        self.assertEqual(0, len(get_current_workloads(docker_client)))

        docker_client.add_container(BadContainer())

        current_workloads = get_current_workloads(docker_client)
        self.assertEqual(0, len(current_workloads))

    @staticmethod
    def __get_test_container(name, thread_count):
        return MockContainer(Workload(name, thread_count, STATIC))
