import json
import time
import uuid

from tests.event.mock_titus_environment import MOCK_TITUS_ENVIRONMENT
from tests.utils import DEFAULT_TEST_MEM, DEFAULT_TEST_DISK, DEFAULT_TEST_NETWORK, DEFAULT_TEST_IMAGE, \
    DEFAULT_TEST_APP_NAME, DEFAULT_TEST_JOB_TYPE, DEFAULT_TEST_OWNER_EMAIL, DEFAULT_TEST_CMD, DEFAULT_TEST_ENTRYPOINT, \
    DEFAULT_TEST_OPPORTUNISTIC_THREAD_COUNT
from titus_isolate import log
from titus_isolate.event.constants import ACTION, ACTOR, ATTRIBUTES, CONTAINER, CREATE, ID, \
    LOWERCASE_ID, NAME, WORKLOAD_TYPE_LABEL_KEY, TIME, TYPE, DIE, STATIC, REPO_DIGESTS
from titus_isolate.model.workload import Workload


class MockEventProvider:
    def __init__(self, events, sleep=0):
        self.__events = events
        self.__sleep = sleep
        self.__closed = False

    def __iter__(self):
        return self

    def __next__(self):
        while len(self.__events) <= 0:
            # Subscribing to Docker events never exits, so we simulate that here
            if self.__closed:
                raise StopIteration("Event stream has been closed")
            time.sleep(0.01)

        time.sleep(self.__sleep)
        return self.__events.pop(0)

    def close(self):
        self.__closed = True


class MockImage:
    def __init__(self, attrs):
        self.attrs = attrs


class MockContainer:
    def __init__(self, workload):
        self.name = workload.get_id()
        self.labels = {}
        self.update_calls = []
        repo_digests = ["registry:7002/name@sha256:digest"]
        attrs = {
            REPO_DIGESTS: repo_digests
        }
        self.image = MockImage(attrs)

    def update(self, **kwargs):
        log.info("update called with: '{}'".format(kwargs))
        threads = kwargs["cpuset_cpus"].split(',')
        self.update_calls.append(threads)


class MockContainerList:
    def __init__(self, containers):
        self.__containers = {}
        for c in containers:
            self.__containers[c.name] = c

    def get(self, name):
        return self.__containers[name]

    def list(self):
        return list(self.__containers.values())

    def _add_container(self, container):
        self.__containers[container.name] = container


class MockDockerClient:
    def __init__(self, containers=[]):
        self.containers = MockContainerList(containers)

    def add_container(self, container):
        self.containers._add_container(container)


def get_container_create_event(cpus, workload_type=STATIC, name=str(uuid.uuid4()).replace("-", ""), id=str(uuid.uuid4()).replace("-", "")):
    attributes = {
        NAME: name,
        WORKLOAD_TYPE_LABEL_KEY: workload_type
    }
    MOCK_TITUS_ENVIRONMENT.add_workload(Workload(
        identifier=name,
        thread_count=cpus,
        mem=DEFAULT_TEST_MEM,
        disk=DEFAULT_TEST_DISK,
        network=DEFAULT_TEST_NETWORK,
        app_name=DEFAULT_TEST_APP_NAME,
        owner_email=DEFAULT_TEST_OWNER_EMAIL,
        image=DEFAULT_TEST_IMAGE,
        command=DEFAULT_TEST_CMD,
        entrypoint=DEFAULT_TEST_ENTRYPOINT,
        job_type=DEFAULT_TEST_JOB_TYPE,
        workload_type=workload_type,
        opportunistic_thread_count=DEFAULT_TEST_OPPORTUNISTIC_THREAD_COUNT))

    return get_event(CONTAINER, CREATE, id, attributes)


def get_container_die_event(name=str(uuid.uuid4()).replace("-", ""), id=str(uuid.uuid4()).replace("-", "")):
    attributes = {
        NAME: name
    }

    return get_event(CONTAINER, DIE, id, attributes)


def get_event(type, action, container_id, attributes):
    return json.dumps({
        LOWERCASE_ID: str(container_id),
        TYPE: str(type),
        ACTION: str(action),
        ACTOR: {
            ID: str(container_id),
            ATTRIBUTES: attributes,
        },
        TIME: int(time.time())
    }).encode("utf-8")
