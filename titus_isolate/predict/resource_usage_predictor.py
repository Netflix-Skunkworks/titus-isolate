import json
import os
from typing import Dict, List, Optional

import requests
from kubernetes.client import V1Pod
from kubernetes.utils.quantity import parse_quantity

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import PREDICTION_SERVICE_URL_FORMAT_STR, CREDENTIALS_PATH
from titus_isolate.model.kubernetes_workload import KubernetesWorkload
from titus_isolate.model.pod_utils import get_job_descriptor, get_start_time, get_main_container_status
from titus_isolate.model.workload_interface import Workload
from titus_isolate.monitor.resource_usage import GlobalResourceUsage
from titus_isolate.crd.model.resource_usage_prediction import ResourceUsagePrediction, ResourceUsagePredictions, Resources
from titus_isolate.predict.simple_cpu_predictor import SimpleCpuPredictor
from titus_isolate.utils import get_config_manager, get_pod_manager

CPU = "cpu"
MEM = "mem"
NET_RECV = "net_recv"
NET_TRANS = "net_trans"
DISK = "disk"

RESOURCE_HEADING_MAPPINGS = {
    CPU_USAGE: CPU,
    MEM_USAGE: MEM,
    NET_RECV_USAGE: NET_RECV,
    NET_TRANS_USAGE: NET_TRANS,
    DISK_USAGE: DISK
}


def __get_credential_path(config_manager: ConfigManager, file_name: str) -> Optional[str]:
    credentials_path = config_manager.get_str(CREDENTIALS_PATH)
    if credentials_path is None:
        return None

    return os.path.join(credentials_path, file_name)


def get_client_cert_path(config_manager: ConfigManager) -> Optional[str]:
    return __get_credential_path(config_manager, 'client.crt')


def get_client_key_path(config_manager: ConfigManager) -> Optional[str]:
    return __get_credential_path(config_manager, 'client.key')


def get_url(config_manager: ConfigManager) -> Optional[str]:
    url_format = config_manager.get_str(PREDICTION_SERVICE_URL_FORMAT_STR)
    if url_format is None:
        return None

    return url_format.format(config_manager.get_region(), config_manager.get_environment())


def get_predictions(client_cert_path: str, client_key_path: str, url: str, body: dict) -> Optional[dict]:
    log.debug("url: %s, body: %s", url, body)
    response = requests.get(
        url,
        json=body,
        cert=(client_cert_path, client_key_path),
        verify=False)
    if response.status_code != 200:
        log.error("Failed to query resource prediction service: %s", response.content)
        return None

    resp_bytes = response.content
    resp_str = resp_bytes.decode('utf8')
    resp_json = json.loads(resp_str.strip())
    return resp_json


def get_first_window_cpu_prediction(prediction: ResourceUsagePrediction):
    cpu_predictions = prediction.resource_type_predictions[CPU]
    p95_cpu_predictions = cpu_predictions.predictions['p95']
    return p95_cpu_predictions[0]


def get_first_window_cpu_predictions(predictions: ResourceUsagePredictions):
    simple_predictions = {}
    for w_id, prediction in predictions.predictions.items():
        simple_predictions[w_id] = get_first_window_cpu_prediction(prediction)


class ResourceUsagePredictor(SimpleCpuPredictor):

    @staticmethod
    def __translate_usage(usages: Dict[str, List[float]]) -> dict:
        out_usage = {}
        for resource_name, values in usages.items():
            out_usage[RESOURCE_HEADING_MAPPINGS[resource_name]] = values[:60]

        return out_usage

    def __get_job_body(self, pod: V1Pod, resource_usage: GlobalResourceUsage):
        return {
            "job_id": pod.metadata.name,
            "job_descriptor": get_job_descriptor(pod),
            "task_data": {
                "started_ts_ms": str(get_start_time(pod)),
                "past_usage": self.__translate_usage(
                    resource_usage.get_all_usage_for_workload(pod.metadata.name))
            }
        }

    def __get_body(self, pods: List[V1Pod], resource_usage: GlobalResourceUsage) -> Optional[dict]:
        return {
            "jobs": [self.__get_job_body(p, resource_usage) for p in pods]
        }

    @staticmethod
    def is_running(pod: V1Pod) -> bool:
        if pod.status.phase != "Running":
            log.info("Pod phase is %s, not Running", pod.status.phase)
            return False

        status = get_main_container_status(pod)
        if status is None:
            log.info("Couldn't find the main container's status")
            return False

        running = status.state.running
        if running is None:
            log.info("Container status state is not running")
            return False

        return True

    def get_cpu_predictions(self, workloads: List[Workload], resource_usage: GlobalResourceUsage) -> Optional[Dict[str, float]]:
        pod_manager = get_pod_manager()
        if pod_manager is None:
            return None

        pods = []
        for w in workloads:
            pod = pod_manager.get_pod(w.get_id())
            if pod is None:
                log.warning("Failed to get pod for workload: %s", w.get_id())
            else:
                pods.append(pod)

        resource_usage_predictions = self.get_predictions(pods, resource_usage)

        predictions = {}
        if resource_usage_predictions is None:
            log.error("Got no resource usage predictions")
            return predictions
        else:
            log.info("Got resource usage predictions: %s", json.dumps(resource_usage_predictions.raw))

        for w_id, prediction in resource_usage_predictions.predictions.items():
            predictions[w_id] = get_first_window_cpu_prediction(prediction)

        return predictions

    def get_predictions(self,
                        pods: List[V1Pod],
                        resource_usage: GlobalResourceUsage) -> Optional[ResourceUsagePredictions]:
        config_manager = get_config_manager()
        if config_manager is None:
            log.warning("Config manager not yet set.")
            return None

        running_pods = []
        for p in pods:
            if self.is_running(p):
                running_pods.append(p)
            else:
                log.info("Pod is not yet running: %s", p.metadata.name)

        client_crt = get_client_cert_path(config_manager)
        client_key = get_client_key_path(config_manager)
        if client_crt is None or client_key is None:
            log.error("Failed to generate credential paths")
            return None

        url = get_url(config_manager)
        if url is None:
            log.error("Unable to generate prediction service url")
            return None

        body = self.__get_body(running_pods, resource_usage)
        if body is None:
            log.error("Unable to generate a prediction request body")
            return None

        predictions = get_predictions(client_crt, client_key, url, body)
        if predictions is None:
            log.error("Failed to get predictions")
            return None

        requested_resources = Resources()
        for pod in pods:
            r = pod.spec.containers[0].resources.requests
            requested_resources += Resources(
                int(parse_quantity(r['cpu'])),
                int(parse_quantity(r['memory'])),
                int(parse_quantity(r['ephemeral-storage'])),
                int(parse_quantity(r['titus/network'])),
                int(parse_quantity(r['nvidia.com/gpu']))
            )
        meta = predictions.get('meta_data', {})
        if meta is None:
            meta = {}
        meta['allocated_resources'] = {
            'cpu': requested_resources.cpu,
            'mem_MB': requested_resources.mem_MB,
            'disk_MB': requested_resources.disk_MB,
            'net_Mbps': requested_resources.net_Mbps,
            'gpu': requested_resources.gpu
        }
        predictions['meta_data'] = meta

        return ResourceUsagePredictions(predictions)
