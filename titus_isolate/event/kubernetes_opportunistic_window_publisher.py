import json
from datetime import datetime, timedelta
from dateutil.parser import parse

import kubernetes
from kubernetes.client import V1Node, V1ObjectMeta, V1OwnerReference, V1DeleteOptions

from titus_isolate import log
from titus_isolate.config.constants import EC2_INSTANCE_ID, OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS_KEY, \
    DEFAULT_OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS
from titus_isolate.event.opportunistic_window_publisher import OpportunisticWindowPublisher
from titus_isolate.event.utils import unix_time_millis, is_int
from titus_isolate.model.opportunistic_resource import OPPORTUNISTIC_RESOURCE_NAMESPACE, \
    OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY, OPPORTUNISTIC_RESOURCE_NODE_UID_LABEL_KEY, OpportunisticResource, \
    OPPORTUNISTIC_RESOURCE_VERSION, OPPORTUNISTIC_RESOURCE_GROUP, OPPORTUNISTIC_RESOURCE_PLURAL
from titus_isolate.model.opportunistic_resource_capacity import OpportunisticResourceCapacity
from titus_isolate.model.opportunistic_resource_spec import OpportunisticResourceSpec
from titus_isolate.model.opportunistic_resource_window import OpportunisticResourceWindow
from titus_isolate.utils import get_config_manager

VIRTUAL_KUBELET_CONFIG_PATH = '/run/virtual-kubelet.config'
KUBECONFIG_ENVVAR = 'KUBECONFIG'
DEFAULT_KUBECONFIG_PATH = '/run/kubernetes/config'


class KubernetesOpportunisticWindowPublisher(OpportunisticWindowPublisher):

    def __init__(self):
        self.__config_manager = get_config_manager()
        self.__node_name = self.__config_manager.get_str(EC2_INSTANCE_ID)

        kubeconfig = self.get_kubeconfig_path()
        self.__core_api = kubernetes.client.CoreV1Api(
            kubernetes.config.new_client_from_config(config_file=kubeconfig))
        # NOTE[jigish]:  This API depends on the OpportunisticResource CRD. See the readme for how to create it.
        self.__custom_api = kubernetes.client.CustomObjectsApi(
            kubernetes.config.new_client_from_config(config_file=kubeconfig))

    @staticmethod
    def get_kubeconfig_path():
        with open(VIRTUAL_KUBELET_CONFIG_PATH) as file:
            line = file.readline()
            while line:
                if line.startswith(KUBECONFIG_ENVVAR + '='):
                    return line.strip()[len(KUBECONFIG_ENVVAR) + 1:]
                line = file.readline()
        return DEFAULT_KUBECONFIG_PATH

    def __get_node(self) -> V1Node:
        node = self.__core_api.read_node(self.__node_name)
        log.debug('node: %s', node)
        return node

    def is_window_active(self) -> bool:
        oppo_list = self.__get_scoped_opportunistic_resources()
        log.debug('is active: oppo list: %s', json.dumps(oppo_list))
        for item in oppo_list['items']:
            log.debug('checking for window: %s', json.dumps(item))
            now = datetime.utcnow()
            if now < self.__get_timestamp(item['spec']['window']['end']):
                return True
        return False

    def cleanup(self):
        oppo_list = self.__get_scoped_opportunistic_resources()
        log.debug('cleanup: oppo list: %s', json.dumps(oppo_list))
        clean_count = 0
        check_secs = self.__config_manager.get_float(OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS_KEY,
                                                     DEFAULT_OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS)
        if check_secs <= 0:
            log.info('configured to skip cleanup. opportunistic resource windows will not be deleted.')
            return 0
        for item in oppo_list['items']:
            check_time = datetime.utcnow() + timedelta(seconds=-1*check_secs)
            if check_time < self.__get_timestamp(item['spec']['window']['end']):
                continue
            log.debug('deleting: %s', json.dumps(item))
            delete_opts = V1DeleteOptions(grace_period_seconds=0, propagation_policy='Foreground')
            resp = self.__custom_api.delete_namespaced_custom_object(version=OPPORTUNISTIC_RESOURCE_VERSION,
                                                                     group=OPPORTUNISTIC_RESOURCE_GROUP,
                                                                     plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                                     namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                                     name=item['metadata']['name'],
                                                                     body=delete_opts)
            log.debug('deleted: %s', json.dumps(resp))
            clean_count += 1

        return clean_count

    def add_window(self, start: datetime, end: datetime, free_cpu_count: int):
        node = self.__get_node()
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
                                                                 group=OPPORTUNISTIC_RESOURCE_GROUP,
                                                                 plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                                 namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                                 body=oppo_body)
        log.debug('created window: %s', json.dumps(oppo))

    def __get_scoped_opportunistic_resources(self):
        label_selector = "{}={}".format(OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY,
                                        self.__node_name)
        return self.__custom_api.list_namespaced_custom_object(version=OPPORTUNISTIC_RESOURCE_VERSION,
                                                               group=OPPORTUNISTIC_RESOURCE_GROUP,
                                                               plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                               namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                               label_selector=label_selector)

    @staticmethod
    def __get_timestamp(s: str) -> datetime:
        if is_int(s):
            return datetime.fromtimestamp(int(s) / 1000)
        else:
            return parse(s)
