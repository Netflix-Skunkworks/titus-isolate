import json
import time
from datetime import datetime as dt
from typing import List, Tuple

import kubernetes
from kubernetes.client import V1ObjectMeta, V1OwnerReference, V1Pod
from kubernetes.client.rest import ApiException

from titus_isolate import log
from titus_isolate.crd.model.resource_usage_prediction import ResourceUsagePredictionsResource, \
    PREDICTED_RESOURCE_USAGE_NAMESPACE, PREDICTED_RESOURCE_USAGE_NODE_NAME_LABEL_KEY, \
    PREDICTED_RESOURCE_USAGE_NODE_UID_LABEL_KEY, PREDICTED_RESOURCE_USAGE_PLURAL, CondensedResourceUsagePrediction, \
    ResourceUsagePredictions
from titus_isolate.crd.model.resources import Resources
from titus_isolate.crd.publish.kubernetes_opportunistic_window_publisher import DEFAULT_KUBECONFIG_PATH
from titus_isolate.kub.utils import get_node, get_instance_type
from titus_isolate.metrics.constants import PARSE_POD_REQUESTED_RESOURCES_FAIL_COUNT
from titus_isolate.model.constants import CUSTOM_RESOURCE_GROUP, PREDICTED_USAGE_RESOURCE_VERSION
from titus_isolate.monitor.workload_monitor_manager import WorkloadMonitorManager
from titus_isolate.pod.pod_manager import PodManager
from titus_isolate.pod.utils import get_requested_resources, is_batch_pod, is_service_pod
from titus_isolate.predict.resource_usage_predictor import ResourceUsagePredictor


class KubernetesPredictedUsagePublisher:

    def __init__(self,
                 resource_usage_predictor: ResourceUsagePredictor,
                 pod_manager: PodManager,
                 workload_monitor_manager: WorkloadMonitorManager):
        self.__resources_capacity = Resources()
        self.__resources_capacity.populate_from_capacity_env()
        self.__resource_usage_predictor = resource_usage_predictor
        self.__pod_manager = pod_manager
        self.__wmm = workload_monitor_manager
        self.__custom_api = kubernetes.client.CustomObjectsApi(
            kubernetes.config.new_client_from_config(config_file=DEFAULT_KUBECONFIG_PATH))
        self.__registry = None
        self.__parse_pod_req_resources_fail_count = 0

    def publish(self):
        log.info("Predicting resource usage")

        allocated_resources = Resources()
        num_batch_containers = 0
        num_service_containers = 0
        if len(self.__pod_manager.get_pods()) == 0:
            log.warning("No pods, skipping resource usage prediction")
            predictions = ResourceUsagePredictions({})
            predictions.set_prediction_ts_ms(1000*int(time.mktime(dt.utcnow().timetuple())))
        else:
            running_pods = [p for p in self.__pod_manager.get_pods() if self.__resource_usage_predictor.is_running(p)]
            try:
                allocated_resources = self.__compute_allocated_resources(running_pods)
            except Exception as e:
                self.__parse_pod_req_resources_fail_count += 1
                log.error("Failed to parse pod requested resources. Aborting: %s", e)
                raise e
            workload_ids = [p.metadata.name for p in running_pods]
            predictions = self.__resource_usage_predictor.get_predictions(
                running_pods,
                self.__wmm.get_resource_usage(workload_ids))
            num_batch_containers, num_service_containers = self.__compute_num_containers(running_pods)

        node = get_node()
        log.debug('owner_kind:%s owner_name:%s owner_uid:%s', node.kind, node.metadata.name, node.metadata.uid)
        instance_type = get_instance_type(node)

        condensed_predictions = CondensedResourceUsagePrediction(
            predictions, allocated_resources, instance_type,
            num_batch_containers, num_service_containers,
            self.__resources_capacity)

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
            obj = self.__custom_api.patch_namespaced_custom_object(version=PREDICTED_USAGE_RESOURCE_VERSION,
                                                                   group=CUSTOM_RESOURCE_GROUP,
                                                                   plural=PREDICTED_RESOURCE_USAGE_PLURAL,
                                                                   namespace=PREDICTED_RESOURCE_USAGE_NAMESPACE,
                                                                   name=object_name,
                                                                   body=body)
        except ApiException as e:
            log.info("ApiException status: %s", e.status)
            if e.status == 404:
                obj = self.__custom_api.create_namespaced_custom_object(version=PREDICTED_USAGE_RESOURCE_VERSION,
                                                                        group=CUSTOM_RESOURCE_GROUP,
                                                                        plural=PREDICTED_RESOURCE_USAGE_PLURAL,
                                                                        namespace=PREDICTED_RESOURCE_USAGE_NAMESPACE,
                                                                        body=body)
            else:
                log.error("Encountered unexpected API exception reason")

        log.info('predicted resource usage: %s', json.dumps(obj))

    @staticmethod
    def __compute_allocated_resources(running_pods: List[V1Pod]) -> Resources:
        tot_resources = Resources()
        for pod in running_pods:
            tot_resources += get_requested_resources(pod)
        return tot_resources

    @staticmethod
    def __compute_num_containers(running_pods : List[V1Pod]) -> Tuple[int, int]:
        num_batch, num_service = 0, 0
        for pod in running_pods:
            if is_batch_pod(pod):
                num_batch += 1
            elif is_service_pod(pod):
                num_service += 1
        return (num_batch, num_service)

    def set_registry(self, registry, tags):
        self.__registry = registry

    def report_metrics(self, tags):
        self.__registry.counter(PARSE_POD_REQUESTED_RESOURCES_FAIL_COUNT, tags).increment(self.__parse_pod_req_resources_fail_count)
        self.__parse_pod_req_resources_fail_count = 0