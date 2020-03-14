import json
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, List

from dateutil.parser import parse
import kubernetes.client
import kubernetes.config
from kubernetes.client.rest import ApiException
from kubernetes.client.models import V1DeleteOptions, V1ObjectMeta, V1OwnerReference

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE
from titus_isolate.config.constants import TOTAL_THRESHOLD, DEFAULT_TOTAL_THRESHOLD, \
    OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS_KEY, \
    DEFAULT_OVERSUBSCRIBE_CLEANUP_AFTER_SECONDS, \
    OVERSUBSCRIBE_WINDOW_SIZE_MINUTES_KEY, \
    DEFAULT_OVERSUBSCRIBE_WINDOW_SIZE_MINUTES, EC2_INSTANCE_ID, \
    DEFAULT_OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE, OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE_KEY
from titus_isolate.event.constants import ACTION, OVERSUBSCRIBE
from titus_isolate.event.event_handler import EventHandler
from titus_isolate.event.utils import unix_time_millis, is_int
from titus_isolate.metrics.constants import OVERSUBSCRIBE_FAIL_COUNT, OVERSUBSCRIBE_SKIP_COUNT, \
                                            OVERSUBSCRIBE_SUCCESS_COUNT, OVERSUBSCRIBE_RECLAIMED_CPU_COUNT
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.opportunistic_resource import OpportunisticResource, OPPORTUNISTIC_RESOURCE_GROUP, \
                                                       OPPORTUNISTIC_RESOURCE_VERSION, \
                                                       OPPORTUNISTIC_RESOURCE_NAMESPACE, \
                                                       OPPORTUNISTIC_RESOURCE_PLURAL, \
                                                       OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY, \
                                                       OPPORTUNISTIC_RESOURCE_NODE_UID_LABEL_KEY
from titus_isolate.model.opportunistic_resource_capacity import OpportunisticResourceCapacity
from titus_isolate.model.opportunistic_resource_spec import OpportunisticResourceSpec
from titus_isolate.model.opportunistic_resource_window import OpportunisticResourceWindow
from titus_isolate.model.workload import get_duration
from titus_isolate.predict.cpu_usage_predictor import PredEnvironment
from titus_isolate.utils import get_config_manager, get_workload_monitor_manager, get_cpu_usage_predictor_manager

CRD_VERSION = 'apiextensions.k8s.io/v1beta1'
CRD_KIND = 'CustomResourceDefinition'

VIRTUAL_KUBELET_CONFIG_PATH = '/run/virtual-kubelet.config'
KUBECONFIG_ENVVAR = 'KUBECONFIG'
DEFAULT_KUBECONFIG_PATH = '/run/kubernetes/config'


def get_kubeconfig_path():
    with open(VIRTUAL_KUBELET_CONFIG_PATH) as file:
        line = file.readline()
        while line:
            if line.startswith(KUBECONFIG_ENVVAR+'='):
                return line.strip()[len(KUBECONFIG_ENVVAR)+1:]
            line = file.readline()
    return DEFAULT_KUBECONFIG_PATH


class OversubscribeEventHandler(EventHandler, MetricsReporter):

    def __init__(self, workload_manager):
        super().__init__(workload_manager)
        self.__reg = None
        self.__fail_count = 0
        self.__skip_count = 0
        self.__success_count = 0
        self.__reclaimed_cpu_count = None

        self.__config_manager = get_config_manager()
        self.__workload_monitor_manager = get_workload_monitor_manager()
        self.__cpu_usage_predictor_manager = get_cpu_usage_predictor_manager()

        self.__node_name = self.__config_manager.get_str(EC2_INSTANCE_ID)
        kubeconfig = get_kubeconfig_path()
        self.__core_api = kubernetes.client.CoreV1Api(
            kubernetes.config.new_client_from_config(config_file=kubeconfig))
        # NOTE[jigish]:  This API depends on the OpportunisticResource CRD. See the readme for how to create it.
        self.__custom_api = kubernetes.client.CustomObjectsApi(
            kubernetes.config.new_client_from_config(config_file=kubeconfig))

    def set_registry(self, registry, tags):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(OVERSUBSCRIBE_FAIL_COUNT, tags).set(self.get_fail_count())
        self.__reg.gauge(OVERSUBSCRIBE_SKIP_COUNT, tags).set(self.get_skip_count())
        self.__reg.gauge(OVERSUBSCRIBE_SUCCESS_COUNT, tags).set(self.get_success_count())
        if self.get_reclaimed_cpu_count() is not None:
            self.__reg.gauge(OVERSUBSCRIBE_RECLAIMED_CPU_COUNT, tags).set(self.get_reclaimed_cpu_count())

    def get_fail_count(self):
        return self.__fail_count

    def get_skip_count(self):
        return self.__skip_count

    def get_success_count(self):
        return self.__success_count

    def get_reclaimed_cpu_count(self):
        return self.__reclaimed_cpu_count

    def handle(self, event):
        Thread(target=self.__handle, args=[event]).start()

    def __handle(self, event):
        try:
            if not self.__relevant(event):
                return

            self.handling_event(event, 'oversubscribing workloads')

            log.info('cleaning up old opportunistic resources')
            clean_count = self.__cleanup()
            log.info('cleaned up %d old opportunistic resources', clean_count)

            pcp_usage = self.__workload_monitor_manager.get_pcp_usage()
            cpu_usage = pcp_usage.get(CPU_USAGE, {})
            pred_env = PredEnvironment(self.__config_manager.get_region(), self.__config_manager.get_environment(),
                                       datetime.utcnow().hour)

            if self.__is_window_active():
                self.__skip_count += 1
                self.handled_event(event, 'skipping oversubscribe - a window is currently active')
                return

            workload_count = 0
            underutilized_cpu_count = 0
            # we calculate the window before we send the request to ensure we're not going over our 10 minute mark
            start = datetime.utcnow()
            end = start + timedelta(minutes=self.__config_manager.get_int(OVERSUBSCRIBE_WINDOW_SIZE_MINUTES_KEY,
                                                                          DEFAULT_OVERSUBSCRIBE_WINDOW_SIZE_MINUTES))
            for workload in self.workload_manager.get_workloads():
                log.info('workload:%s job_type:%s cpu:%d', workload.get_app_name(), workload.get_job_type(),
                          workload.get_thread_count())

                is_oversubscribable = self.__is_oversubscribable(workload, cpu_usage, pred_env)
                log.info("Workload: {} is oversubscribable: {}".format(workload.get_id(), is_oversubscribable))
                if not is_oversubscribable:
                    log.info("Workload: {} is NOT oversubscribable: {}".format(workload.get_id(), is_oversubscribable))
                    continue

                if workload.is_opportunistic():
                    # only add the number of "real" threads (non-opportunistic)
                    free = workload.get_thread_count() - workload.get_opportunistic_thread_count()
                    if free <= 0:
                        continue
                    underutilized_cpu_count += free
                else:
                    underutilized_cpu_count += workload.get_thread_count()
                workload_count += 1

            free_cpu_count = underutilized_cpu_count
            if free_cpu_count > 0:
                self.__add_window(start, end, free_cpu_count)

            self.__success_count += 1
            self.__reclaimed_cpu_count = underutilized_cpu_count
            self.handled_event(event,
                               'oversubscribed {} cpus from {} workloads, {} total cpus are oversubscribed'.format(
                                   free_cpu_count, workload_count, underutilized_cpu_count))
        except:
            log.exception("Event handler: '{}' failed to handle event: '{}'".format(
                self.__class__.__name__, event))

    def __relevant(self, event):
        if not event[ACTION] == OVERSUBSCRIBE:
            self.ignored_event(event, 'not a {} event'.format(OVERSUBSCRIBE))
            return False

        return True

    @staticmethod
    def __get_timestamp(s: str) -> datetime:
        if is_int(s):
            return datetime.fromtimestamp(int(s) / 1000)
        else:
            return parse(s)

    def __get_scoped_opportunistic_resources(self):
        label_selector = "{}={}".format(OPPORTUNISTIC_RESOURCE_NODE_NAME_LABEL_KEY,
                                        self.__node_name)
        return self.__custom_api.list_namespaced_custom_object(version=OPPORTUNISTIC_RESOURCE_VERSION,
                                                               group=OPPORTUNISTIC_RESOURCE_GROUP,
                                                               plural=OPPORTUNISTIC_RESOURCE_PLURAL,
                                                               namespace=OPPORTUNISTIC_RESOURCE_NAMESPACE,
                                                               label_selector=label_selector)

    def __cleanup(self):
        try:
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
        except ApiException as e:
            log.error('Exception when calling CustomObjectsApi->list_namespaced_custom_object: %s', e)
            self.__fail_count += 1
            raise e

    def __get_workload_duration(self, workload, min_duration_sec) -> float:
        if workload.is_service():
            return min_duration_sec

        duration_percentile = self.__config_manager.get_float(OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE_KEY,
                                                              DEFAULT_OVERSUBSCRIBE_BATCH_DURATION_PERCENTILE)
        duration = get_duration(workload, duration_percentile)
        return duration if duration is not None else -1

    def __is_oversubscribable(self, workload, cpu_usage: Dict[str, List], pred_env) -> bool:
        min_duration_sec = 60 * self.__config_manager.get_int(OVERSUBSCRIBE_WINDOW_SIZE_MINUTES_KEY,
                                                              DEFAULT_OVERSUBSCRIBE_WINDOW_SIZE_MINUTES)
        workload_duration_sec = self.__get_workload_duration(workload, min_duration_sec)
        if workload_duration_sec < min_duration_sec:
            log.info("Workload: {} is too short. workload_duration_sec: {} < min_duration_sec: {}".format(workload.get_id(), workload_duration_sec, min_duration_sec))
            return False

        log.info("Workload: {} is long enough. workload_duration_sec: {} >= min_duration_sec: {}".format(workload.get_id(), workload_duration_sec, min_duration_sec))

        if workload.get_id() not in list(cpu_usage.keys()):
            log.info("No cpu usage data for workload: {} in keys: {}".format(workload.get_id(), list(cpu_usage.keys())))
            return False

        workload_cpu_usage = cpu_usage[workload.get_id()]
        log.info("workload: {}, workload_cpu_usage: {}".format(workload.get_id(), workload_cpu_usage))
        workload_cpu_usage = [float(u) for u in workload_cpu_usage]
        pred_cpus = self.__cpu_usage_predictor_manager.get_predictor().predict(workload,
                                                                               workload_cpu_usage,
                                                                               pred_env)
        pred_usage = pred_cpus / workload.get_thread_count()
        threshold = self.__config_manager.get_float(TOTAL_THRESHOLD, DEFAULT_TOTAL_THRESHOLD)

        log.info("Testing oversubscribability of workload: {}, threshold: {}, prediction: {}".format(workload.get_id(), threshold, pred_usage))
        if pred_usage > threshold:
            return False

        log.debug(' --> low utilization (%f), oversubscribing', pred_usage)
        return True

    def __get_node(self):
        try:
            node = self.__core_api.read_node(self.__node_name)
            log.debug('node: %s', node)
            return node
        except ApiException as e:
            log.error('Exception when calling CoreV1Api->read_node: %s', e)
            self.__fail_count += 1
            raise e

    def __is_window_active(self):
        try:
            oppo_list = self.__get_scoped_opportunistic_resources()
            log.debug('is active: oppo list: %s', json.dumps(oppo_list))
            for item in oppo_list['items']:
                log.debug('checking for window: %s', json.dumps(item))
                now = datetime.utcnow()
                if now < self.__get_timestamp(item['spec']['window']['end']):
                    return True
            return False
        except ApiException as e:
            log.error('Exception when calling CustomObjectsApi->list_namespaced_custom_object: %s', e)
            self.__fail_count += 1
            raise e

    def __add_window(self, start: datetime, end: datetime, free_cpu_count: int):
        node = self.__get_node()
        log.debug('owner_kind:%s owner_name:%s owner_uid:%s', node.kind, node.metadata.name, node.metadata.uid)
        start_epoch_ms = int(unix_time_millis(start))
        end_epoch_ms = int(unix_time_millis(end))

        # add opportunistic resource
        try:
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
        except ApiException as e:
            log.error('Exception when calling CustomObjectsApi->create_namespaced_custom_object: %s', e)
            self.__fail_count += 1
            raise e
