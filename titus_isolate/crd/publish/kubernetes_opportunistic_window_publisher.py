import json
from datetime import datetime, timedelta
from threading import Thread, Lock

from dateutil.parser import parse

import kubernetes
from kubernetes.client import V1ObjectMeta, V1OwnerReference, V1DeleteOptions
from kubernetes import watch

from titus_isolate import log
from titus_isolate.config.constants import OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS_KEY, \
    DEFAULT_OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS, OVERSUBSCRIBE_FREQUENCY_KEY, DEFAULT_OVERSUBSCRIBE_FREQUENCY
from titus_isolate.constants import DEFAULT_KUBECONFIG_PATH, OPPORTUNISTIC_WATCH_FAILURE
from titus_isolate.crd.publish.opportunistic_window_publisher import OpportunisticWindowPublisher
from titus_isolate.event.utils import unix_time_millis, is_int
from titus_isolate.exit_handler import ExitHandler
from titus_isolate.kub.utils import get_node, get_node_name
from titus_isolate.crd.model.opportunistic_resource import OPPORTUNISTIC_RESOURCE_NAMESPACE, \
    OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY, OPPORTUNISTIC_RESOURCE_NODE_UID_LABEL_KEY, OpportunisticResource, \
    CUSTOM_RESOURCE_GROUP, OPPORTUNISTIC_RESOURCE_PLURAL
from titus_isolate.crd.model.opportunistic_resource_capacity import OpportunisticResourceCapacity
from titus_isolate.crd.model.opportunistic_resource_spec import OpportunisticResourceSpec
from titus_isolate.crd.model.opportunistic_resource_window import OpportunisticResourceWindow
from titus_isolate.model.constants import OPPORTUNISTIC_RESOURCE_VERSION
from titus_isolate.utils import get_config_manager

VIRTUAL_KUBELET_CONFIG_PATH = '/run/virtual-kubelet.config'
KUBECONFIG_ENVVAR = 'KUBECONFIG'

ADDED = "ADDED"
DELETED = "DELETED"
HANDLED_EVENTS = [ADDED, DELETED]

EPOCH = datetime.utcfromtimestamp(0)


class KubernetesOpportunisticWindowPublisher(OpportunisticWindowPublisher):

    def __init__(self, exit_handler: ExitHandler):
        self.__exit_handler = exit_handler
        self.__config_manager = get_config_manager()

        self.__custom_api = kubernetes.client.CustomObjectsApi(
            kubernetes.config.new_client_from_config(config_file=DEFAULT_KUBECONFIG_PATH))

        self.__lock = Lock()
        self.__opportunistic_resources = {}

        oversubscribe_frequency = self.__config_manager.get_float(OVERSUBSCRIBE_FREQUENCY_KEY,
                                                                  DEFAULT_OVERSUBSCRIBE_FREQUENCY)
        if oversubscribe_frequency > 0:
            watch_thread = Thread(target=self.__watch)
            watch_thread.start()
            Thread(target=self.__crash, args=[watch_thread]).start()
        else:
            log.info("Skipping opportunistic resource watch, as opportunistic publishing is not configured.")

    def __crash(self, watch_thread: Thread):
        log.info("Waiting for opportunistic watch thread to exit...")
        watch_thread.join()
        log.error("Opportunistic watch thread has failed. Exiting.")
        self.__exit_handler.exit(OPPORTUNISTIC_WATCH_FAILURE)

    def __watch(self):
        try:
            label_selector = "{}={}".format(OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY,
                                            get_node_name())
            while True:
                log.info("Starting opportunistic resource watch...")
                stream = None
                try:
                    stream = watch.Watch().stream(
                        self.__custom_api.list_namespaced_custom_object,
                        group="titus.netflix.com",
                        version="v1",
                        namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                        plural="opportunistic-resources",
                        label_selector=label_selector)

                    for event in stream:
                        log.info("Event: %s", event)
                        if self.__is_expired_error(event):
                            raise Exception("Opportunistic resource expired")

                        event_type = event['type']
                        if event_type not in HANDLED_EVENTS:
                            log.warning("Ignoring unhandled event: %s", event)
                            continue

                        event_metadata_name = event['object']['metadata']['name']
                        with self.__lock:
                            if event_type == ADDED:
                                self.__opportunistic_resources[event_metadata_name] = event
                            elif event_type == DELETED:
                                self.__opportunistic_resources.pop(event_metadata_name, None)

                except Exception:
                    log.exception("Watch of opportunistic resources failed")
                    if stream is not None:
                        log.error("Attempting to close opportunistic stream")
                        stream.close()
        except Exception:
            log.exception("Opportunistic watch encountered unhandled exception")

        log.error("Opportunistic watch thread is unexpectedly exiting.")

    def is_window_active(self) -> bool:
        with self.__lock:
            log.debug('is active: oppo list: %s', json.dumps(self.__opportunistic_resources))
            for item in self.__opportunistic_resources.values():
                log.debug('checking for window: %s', json.dumps(item))
                now = datetime.utcnow()
                if now < self.__get_timestamp(item['object']['spec']['window']['end']):
                    return True
            return False

    def _is_old_enough_for_gc(self, cleanup_after_seconds: float, end_time: int) -> bool:
        check_secs = self.__config_manager.get_float(OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS_KEY,
                                                     DEFAULT_OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS)
        check_time = datetime.utcnow() - timedelta(seconds=check_secs)
        check_time = (check_time - EPOCH).total_seconds() * 1000
        log.debug("checking check_time < end_time, %s < %s", check_time, end_time)
        return check_time > end_time

    def cleanup(self):
        with self.__lock:
            log.debug('cleanup: oppo list: %s', json.dumps(self.__opportunistic_resources))
            clean_count = 0
            cleanup_after_seconds = self.__config_manager.get_float(OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS_KEY,
                                                                    DEFAULT_OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS)
            if cleanup_after_seconds <= 0:
                log.warning('configured to skip cleanup. opportunistic resource windows will not be deleted.')
                return 0

            for item in self.__opportunistic_resources.values():
                end_time = item['object']['spec']['window']['end']
                if not self._is_old_enough_for_gc(cleanup_after_seconds, end_time):
                    log.info("skipping gc of opportunistic resource: %s", item['object']['metadata']['name'])
                    continue

                log.debug('deleting: %s', json.dumps(item))
                delete_opts = V1DeleteOptions(grace_period_seconds=0, propagation_policy='Foreground')
                resp = self.__custom_api.delete_namespaced_custom_object(version=OPPORTUNISTIC_RESOURCE_VERSION,
                                                                         group=CUSTOM_RESOURCE_GROUP,
                                                                         plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                                         namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                                         name=item['object']['metadata']['name'],
                                                                         body=delete_opts)
                log.debug('deleted: %s', json.dumps(resp))
                clean_count += 1

            return clean_count

    def add_window(self, start: datetime, end: datetime, free_cpu_count: int):
        node = get_node()
        log.debug('owner_kind:%s owner_name:%s owner_uid:%s', node.kind, node.metadata.name, node.metadata.uid)
        start_epoch_ms = int(unix_time_millis(start))
        end_epoch_ms = int(unix_time_millis(end))

        oppo_meta = V1ObjectMeta(namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                 name="{}-{}-{}".format(node.metadata.name, start_epoch_ms, end_epoch_ms),
                                 labels={
                                     OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY: node.metadata.name,
                                     OPPORTUNISTIC_RESOURCE_NODE_UID_LABEL_KEY: node.metadata.uid
                                 },
                                 owner_references=[
                                     V1OwnerReference(api_version=node.api_version,
                                                      kind=node.kind,
                                                      name=node.metadata.name,
                                                      uid=node.metadata.uid)
                                 ])
        oppo_spec = OpportunisticResourceSpec(capacity=OpportunisticResourceCapacity(free_cpu_count),
                                              window=OpportunisticResourceWindow(start_epoch_ms, end_epoch_ms))
        oppo_body = OpportunisticResource(metadata=oppo_meta,
                                          spec=oppo_spec)
        oppo = self.__custom_api.create_namespaced_custom_object(version=OPPORTUNISTIC_RESOURCE_VERSION,
                                                                 group=CUSTOM_RESOURCE_GROUP,
                                                                 plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                                 namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                                 body=oppo_body)
        log.debug('created window: %s', json.dumps(oppo))

    @staticmethod
    def __get_timestamp(s: str) -> datetime:
        if is_int(s):
            return datetime.fromtimestamp(int(s) / 1000)
        else:
            return parse(s)

    def __is_expired_error(self, event: dict) -> bool:
        # {
        # 	'type': 'ERROR',
        # 	'object': {
        # 		'kind': 'Status',
        # 		'apiVersion': 'v1',
        # 		'metadata': {},
        # 		'status': 'Failure',
        # 		'message': 'too old resource version: 43249758 (43249780)',
        # 		'reason': 'Expired',
        # 		'code': 410
        # 	},
        # 	'raw_object': {
        # 		'kind': 'Status',
        # 		'apiVersion': 'v1',
        # 		'metadata': {},
        # 		'status': 'Failure',
        # 		'message': 'too old resource version: 43249758 (43249780)',
        # 		'reason': 'Expired',
        # 		'code': 410
        # 	}
        # }

        is_error = event['type'] == 'ERROR'
        is_expired = False
        if 'code' in event['object']:
            is_expired = event['object']['code'] == 410

        return is_error and is_expired
