import unittest

from tests.event.mock_docker import MockDockerClient, MockContainer
from tests.utils import DEFAULT_TEST_MEM, DEFAULT_TEST_DISK, DEFAULT_TEST_NETWORK, DEFAULT_TEST_IMAGE, \
    DEFAULT_TEST_APP_NAME, DEFAULT_TEST_OWNER_EMAIL, DEFAULT_TEST_JOB_TYPE
from titus_isolate import log
from titus_isolate.event.constants import STATIC, CPU_LABEL_KEY, WORKLOAD_TYPE_LABEL_KEY
from titus_isolate.event.utils import get_current_workloads
from titus_isolate.model.workload import Workload


class BadContainer:
    def update(self, **kwargs):
        log.info("bad container update called with: '{}'".format(kwargs))
        threads = kwargs["cpuset_cpus"].split(',')
        self.update_calls.append(threads)


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

    def test_get_current_missing_label_workload(self):
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

    def test_get_current_missing_label_workload(self):
        # The container is missing an expected label
        class BadLabelContainer(BadContainer):
            def __init__(self):
                self.name = "bad-container"
                self.labels = {
                    CPU_LABEL_KEY: 2,
                }
                self.update_calls = []

        self.__test_get_current_bad_workload(BadLabelContainer())

    def test_get_current_incorrect_type_workload(self):
        # The BadTypeContainer has a non-integer CPU label
        class BadTypeContainer(BadContainer):
            def __init__(self):
                self.name = "bad-container"
                self.labels = {
                    CPU_LABEL_KEY: "x",
                    WORKLOAD_TYPE_LABEL_KEY: STATIC
                }
                self.update_calls = []

        self.__test_get_current_bad_workload(BadTypeContainer())

    def __test_get_current_bad_workload(self, bad_container):
        docker_client = MockDockerClient()
        self.assertEqual(0, len(get_current_workloads(docker_client)))

        docker_client.add_container(bad_container)

        current_workloads = get_current_workloads(docker_client)
        self.assertEqual(0, len(current_workloads))

    @staticmethod
    def __get_test_container(name, thread_count):
        return MockContainer(
            Workload(
                identifier=name,
                thread_count=thread_count,
                mem=DEFAULT_TEST_MEM,
                disk=DEFAULT_TEST_DISK,
                network=DEFAULT_TEST_NETWORK,
                app_name=DEFAULT_TEST_APP_NAME,
                owner_email=DEFAULT_TEST_OWNER_EMAIL,
                image=DEFAULT_TEST_IMAGE,
                job_type=DEFAULT_TEST_JOB_TYPE,
                workload_type=STATIC))
