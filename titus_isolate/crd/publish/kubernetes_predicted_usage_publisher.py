import json
import time
from typing import Optional

import schedule
from kubernetes.client import V1ObjectMeta, V1OwnerReference
from kubernetes.client.rest import ApiException

from titus_isolate import log
from titus_isolate.crd.model.resource_usage_prediction import ResourceUsagePredictionsResource, \
    PREDICTED_RESOURCE_USAGE_NAMESPACE, PREDICTED_RESOURCE_USAGE_NODE_NAME_LABEL_KEY, \
    PREDICTED_RESOURCE_USAGE_NODE_UID_LABEL_KEY, PREDICTED_RESOURCE_USAGE_PLURAL, CondensedResourceUsagePrediction, \
    ResourceUsagePredictions
from titus_isolate.crd.publish.kubernetes_opportunistic_window_publisher import DEFAULT_KUBECONFIG_PATH

import kubernetes

from titus_isolate.kub.utils import get_node
from titus_isolate.model.constants import CUSTOM_RESOURCE_VERSION, CUSTOM_RESOURCE_GROUP
from titus_isolate.monitor.workload_monitor_manager import WorkloadMonitorManager
from titus_isolate.pod.pod_manager import PodManager
from titus_isolate.predict.resource_usage_predictor import ResourceUsagePredictor


class KubernetesPredictedUsagePublisher:

    def __init__(self,
                 resource_usage_predictor: ResourceUsagePredictor,
                 pod_manager: PodManager,
                 workload_monitor_manager: WorkloadMonitorManager):
        self.__resource_usage_predictor = resource_usage_predictor
        self.__pod_manager = pod_manager
        self.__wmm = workload_monitor_manager
        self.__custom_api = kubernetes.client.CustomObjectsApi(
            kubernetes.config.new_client_from_config(config_file=DEFAULT_KUBECONFIG_PATH))

    def publish(self):
        log.info("Predicting resource usage")

        if len(self.__pod_manager.get_pods()) == 0:
            log.warning("No pods, skipping resource usage prediction")
            predictions = ResourceUsagePredictions({})
            predictions.set_prediction_ts_ms(1000*int(time.time()))
        else:
            predictions = self.__resource_usage_predictor.get_predictions(
                self.__pod_manager.get_pods(),
                self.__wmm.get_resource_usage())

        condensed_predictions = CondensedResourceUsagePrediction(predictions)

        node = get_node()
        log.debug('owner_kind:%s owner_name:%s owner_uid:%s', node.kind, node.metadata.name, node.metadata.uid)

        object_name = "{}".format(node.metadata.name)
        metadata = V1ObjectMeta(namespace=PREDICTED_RESOURCE_USAGE_NAMESPACE,
                                name=object_name,
                                labels={
                                    PREDICTED_RESOURCE_USAGE_NODE_NAME_LABEL_KEY: node.metadata.name,
                                    PREDICTED_RESOURCE_USAGE_NODE_UID_LABEL_KEY: node.metadata.uid
                                },
                                owner_references=[
                                    V1OwnerReference(api_version=node.api_version,
                                                     kind=node.kind,
                                                     name=node.metadata.name,
                                                     uid=node.metadata.uid)
                                ])
        body = ResourceUsagePredictionsResource(metadata=metadata,
                                                spec=condensed_predictions)

        obj = "UNINITIALIZED_RESOURCE_PREDICTION_OBJECT"
        try:
            obj = self.__custom_api.patch_namespaced_custom_object(version=CUSTOM_RESOURCE_VERSION,
                                                                   group=CUSTOM_RESOURCE_GROUP,
                                                                   plural=PREDICTED_RESOURCE_USAGE_PLURAL,
                                                                   namespace=PREDICTED_RESOURCE_USAGE_NAMESPACE,
                                                                   name=object_name,
                                                                   body=body)
        except ApiException as e:
            log.info("ApiException status: %s", e.status)
            if e.status == 404:
                obj = self.__custom_api.create_namespaced_custom_object(version=CUSTOM_RESOURCE_VERSION,
                                                                        group=CUSTOM_RESOURCE_GROUP,
                                                                        plural=PREDICTED_RESOURCE_USAGE_PLURAL,
                                                                        namespace=PREDICTED_RESOURCE_USAGE_NAMESPACE,
                                                                        body=body)
            else:
                log.exception("Encountered unexpected API exception reason")

        log.info('predicted resource usage: %s', json.dumps(obj))
