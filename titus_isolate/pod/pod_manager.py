import copy
from threading import Thread, Lock
from typing import List, Optional

from kubernetes import client, config, watch
from kubernetes.client import V1Pod, V1ObjectMeta

from titus_isolate import log
from titus_isolate.utils import get_config_manager

config_file_path = '/run/kubernetes/config'

ADDED = "ADDED"
DELETED = "DELETED"
MODIFIED = "MODIFIED"

TYPE = 'type'
OBJECT = 'object'
METADATA = 'metadata'
NAME = 'name'


def get_pod_object(event: dict) -> V1Pod:
    return event[OBJECT]


def get_pod_metadata(event: dict) -> V1ObjectMeta:
    return get_pod_object(event).metadata


def get_pod_name(event: dict):
    return get_pod_metadata(event).name


class PodManager:
    def __init__(self, config_path=config_file_path):
        self.__lock = Lock()
        self.__pod_cache = {}
        config.load_kube_config(config_file=config_path)

    def get_pod(self, pod_name: str) -> Optional[V1Pod]:
        with self.__lock:
            if pod_name not in self.__pod_cache.keys():
                return None

            return copy.deepcopy(self.__pod_cache.get(pod_name))

    def get_pods(self) -> List[V1Pod]:
        with self.__lock:
            return list(self.__pod_cache.values())

    def start(self):
        Thread(target=self.__watch).start()

    def __watch(self):
        while True:
            try:
                instance_id = get_config_manager().get_str("EC2_INSTANCE_ID")
                field_selector = "spec.nodeName={}".format(instance_id)
                log.info("Watching pods with field selector: %s", field_selector)

                v1 = client.CoreV1Api()
                w = watch.Watch()

                for event in w.stream(v1.list_pod_for_all_namespaces, field_selector=field_selector):
                    self.__handle_event(event)
            except Exception:
                log.error("pod watch thread failed")

    def __handle_event(self, event: dict):
        event_type = event.get(TYPE, None)
        if event_type is None:
            log.error("Failed to determine type of event: %s", event)
            return

        handlers = {
            ADDED: self.__add_pod,
            MODIFIED: self.__modify_pod,
            DELETED: self.__delete_pod
        }

        if event_type not in handlers.keys():
            log.error("Unsupported event type: %s", event_type)
            return

        with self.__lock:
            handlers[event_type](event)

    def __add_pod(self, event):
        pod_name = get_pod_name(event)
        log.debug("Add pod event: %s", pod_name)
        self.__store_pod(event)

    def __modify_pod(self, event):
        pod_name = get_pod_name(event)
        log.debug("Modify pod event: %s", pod_name)
        self.__store_pod(event)

    def __store_pod(self, event):
        self.__pod_cache[get_pod_name(event)] = get_pod_object(event)

    def __delete_pod(self, event):
        pod_name = get_pod_name(event)
        log.debug("Delete pod event: %s", pod_name)
        self.__pod_cache.pop(pod_name, None)