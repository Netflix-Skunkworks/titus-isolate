import json
import time
import uuid

from tests.utils import DEFAULT_TEST_MEM, DEFAULT_TEST_DISK, DEFAULT_TEST_NETWORK, DEFAULT_TEST_IMAGE, \
    DEFAULT_TEST_APP_NAME, DEFAULT_TEST_JOB_TYPE, DEFAULT_TEST_OWNER_EMAIL
from titus_isolate import log
from titus_isolate.event.constants import ACTION, ACTOR, ATTRIBUTES, CONTAINER, CPU_LABEL_KEY, CREATE, ID, \
    LOWERCASE_ID, NAME, TIME, TYPE, DIE, WORKLOAD_TYPE_LABEL_KEY, STATIC, MEM_LABEL_KEY, DISK_LABEL_KEY, \
    NETWORK_LABEL_KEY, IMAGE_LABEL_KEY, REPO_DIGESTS, APP_NAME_LABEL_KEY, JOB_TYPE_LABEL_KEY, OWNER_EMAIL_LABEL_KEY


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
        self.labels = {
            APP_NAME_LABEL_KEY: workload.get_app_name(),
            CPU_LABEL_KEY: str(workload.get_thread_count()),
            MEM_LABEL_KEY: str(workload.get_mem()),
            DISK_LABEL_KEY: str(workload.get_disk()),
            NETWORK_LABEL_KEY: str(workload.get_network()),
            JOB_TYPE_LABEL_KEY: workload.get_job_type(),
            IMAGE_LABEL_KEY: workload.get_image(),
            WORKLOAD_TYPE_LABEL_KEY: workload.get_type(),
            OWNER_EMAIL_LABEL_KEY: workload.get_owner_email()
        }
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
        APP_NAME_LABEL_KEY: DEFAULT_TEST_APP_NAME,
        CPU_LABEL_KEY: str(cpus),
        MEM_LABEL_KEY: DEFAULT_TEST_MEM,
        DISK_LABEL_KEY: DEFAULT_TEST_DISK,
        NETWORK_LABEL_KEY: DEFAULT_TEST_NETWORK,
        JOB_TYPE_LABEL_KEY: DEFAULT_TEST_JOB_TYPE,
        WORKLOAD_TYPE_LABEL_KEY: workload_type,
        OWNER_EMAIL_LABEL_KEY: DEFAULT_TEST_OWNER_EMAIL,
        IMAGE_LABEL_KEY: DEFAULT_TEST_IMAGE,
    }

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
