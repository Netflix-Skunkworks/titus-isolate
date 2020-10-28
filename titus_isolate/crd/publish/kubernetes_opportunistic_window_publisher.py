import json
from datetime import datetime

import kubernetes
from dateutil.parser import parse
from kubernetes.client import V1ObjectMeta, V1OwnerReference

from titus_isolate import log
from titus_isolate.constants import DEFAULT_KUBECONFIG_PATH
from titus_isolate.crd.model.opportunistic_resource import OPPORTUNISTIC_RESOURCE_NAMESPACE, \
    OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY, OPPORTUNISTIC_RESOURCE_NODE_UID_LABEL_KEY, OpportunisticResource, \
    CUSTOM_RESOURCE_GROUP, OPPORTUNISTIC_RESOURCE_PLURAL
from titus_isolate.crd.model.opportunistic_resource_capacity import OpportunisticResourceCapacity
from titus_isolate.crd.model.opportunistic_resource_spec import OpportunisticResourceSpec
from titus_isolate.crd.model.opportunistic_resource_window import OpportunisticResourceWindow
from titus_isolate.crd.publish.opportunistic_window_publisher import OpportunisticWindowPublisher
from titus_isolate.event.utils import unix_time_millis, is_int
from titus_isolate.exit_handler import ExitHandler
from titus_isolate.kub.utils import get_node, get_node_name
from titus_isolate.metrics.constants import OVERSUBSCRIBE_RECLAIMED_CPU_COUNT
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.constants import OPPORTUNISTIC_RESOURCE_VERSION, OPPORTUNISTIC_RESOURCE_TTL
from titus_isolate.utils import get_config_manager

VIRTUAL_KUBELET_CONFIG_PATH = '/run/virtual-kubelet.config'
KUBECONFIG_ENVVAR = 'KUBECONFIG'

ADDED = "ADDED"
DELETED = "DELETED"
HANDLED_EVENTS = [ADDED, DELETED]

EPOCH = datetime.utcfromtimestamp(0)


class KubernetesOpportunisticWindowPublisher(OpportunisticWindowPublisher, MetricsReporter):

    def __init__(self, exit_handler: ExitHandler):
        self.__exit_handler = exit_handler
        self.__config_manager = get_config_manager()
        self.__registry = None
        self.__oppo = None

        self.__custom_api = kubernetes.client.CustomObjectsApi(
            kubernetes.config.new_client_from_config(config_file=DEFAULT_KUBECONFIG_PATH))

    def get_current_end(self) -> datetime:
        label_selector = "{}={}".format(OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY,
                                        get_node_name())
        response = self.__custom_api.list_namespaced_custom_object(version=OPPORTUNISTIC_RESOURCE_VERSION,
                                                                   group=CUSTOM_RESOURCE_GROUP,
                                                                   plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                                   namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                                   label_selector=label_selector)
        items = response["items"]
        if not items: return EPOCH

        return max([self.__get_timestamp(x) for x in items])

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
                                 annotations={
                                     OPPORTUNISTIC_RESOURCE_TTL: '1h',
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
        self.__oppo = oppo
        log.debug('created window: %s', json.dumps(oppo))

    @staticmethod
    def __get_timestamp(item: dict) -> datetime:
        s = item['object']['spec']['window']['end']
        if is_int(s):
            return datetime.fromtimestamp(int(s) / 1000)
        else:
            return parse(s)

    def set_registry(self, registry, tags):
        self.__registry = registry

    def report_metrics(self, tags):
        if self.__oppo is None:
            return

        opp_capacity = int(self.__oppo['object']['spec']['capacity']['cpu'])
        self.__registry.gauge(OVERSUBSCRIBE_RECLAIMED_CPU_COUNT, tags).set(opp_capacity)
