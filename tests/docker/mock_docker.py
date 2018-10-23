import json
import logging
import time
import uuid

from titus_isolate.docker.constants import ACTION, ACTOR, ATTRIBUTES, CONTAINER, CPU_LABEL_KEY, CREATE, ID, \
    LOWERCASE_ID, NAME, TIME, TYPE, DIE, WORKLOAD_TYPE_LABEL_KEY, STATIC

log = logging.getLogger()


class MockEventProvider:
    def __init__(self, events):
        self.__events = events
        self.__closed = False

    def __iter__(self):
        return self

    def __next__(self):
        while len(self.__events) <= 0:
            # Subscribing to Docker events never exits, so we simulate that here
            if self.__closed:
                raise StopIteration("Event stream has been closed")
            time.sleep(0.01)

        return self.__events.pop(0)

    def close(self):
        self.__closed = True


class MockContainer:
    def __init__(self, workload):
        self.name = workload.get_id()
        self.labels = {
            CPU_LABEL_KEY: str(workload.get_thread_count()),
            WORKLOAD_TYPE_LABEL_KEY: workload.get_type()
        }

    @staticmethod
    def update(**kwargs):
        log.info("update called with: '{}'".format(kwargs))


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
        CPU_LABEL_KEY: str(cpus),
        WORKLOAD_TYPE_LABEL_KEY: workload_type
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
            ATTRIBUTES: attributes
        },
        TIME: int(time.time())
    })
