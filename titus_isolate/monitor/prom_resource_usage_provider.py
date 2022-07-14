import json
from datetime import datetime, timedelta
from typing import List
from cachetools import cached, TTLCache

import requests

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE
from titus_isolate.config.constants import PROMETHEUS_HOST_OVERRIDE, PROMETHEUS_SHARDING_ENABLED, \
    DEFAULT_PROMETHEUS_SHARDING_ENABLED
from titus_isolate.monitor.resource_usage import ResourceUsage
from titus_isolate.monitor.resource_usage_provider import ResourceUsageProvider
from titus_isolate.utils import get_config_manager


query_format = {
    CPU_USAGE: 'rate(titus_cpu_cpuacct_usage{{instance="{}",v3_job_titus_netflix_com_task_id=~"{}"}}[1m])',
    MEM_USAGE: 'titus_memory_usage_in_bytes{{instance="{}",v3_job_titus_netflix_com_task_id=~"{}"}}',
    NET_RECV_USAGE: 'rate(titus_network_in_stat_bytes{{instance="{}",v3_job_titus_netflix_com_task_id=~"{}"}}[1m])',
    NET_TRANS_USAGE: 'rate(titus_network_out_stat_bytes{{instance="{}",v3_job_titus_netflix_com_task_id=~"{}"}}[1m])',
    DISK_USAGE: 'titus_disk_bytes_used{{instance="{}",v3_job_titus_netflix_com_task_id=~"{}"}}',
}


def dt2str(dt: datetime) -> str:
    return dt.isoformat("T") + "Z"


def get_prom_shard_discovery_url() -> str:
    cm = get_config_manager()

    # e.g.: titusprometheus-staging01cell001-x10.cluster.us-east-1.test.cloud.netflix.net
    host = f'titusprometheus-{cm.get_stack()}-x10.cluster.{cm.get_region()}.{cm.get_environment()}.cloud.netflix.net'
    port = '9092'

    # This URL evaluates to shard 0 always. We reach out to this well known shard to find out which shard really scrapes
    # the data for the local node.
    return f'http://{host}:{port}/shard'


def get_sharded_prom_url() -> str:
    cm = get_config_manager()
    url = get_prom_shard_discovery_url()
    body = {
        "instance": cm.get_instance()
    }

    log.info(f'prometheus shard discovery url: {url}, body: {body}')

    response = requests.post(url, json=body)
    if response.status_code != 200:
        log.error("Failed to query shard discovery service: %s")
        return "UNKNOWN_SHARDED_PROM_URL"

    resp_bytes = response.content
    resp_str = resp_bytes.decode('utf8')

    log.info(f'prometheus shard discovery response: {resp_str}')
    resp_json = json.loads(resp_str.strip())

    prom_endpoint = resp_json["endpoints"]["prometheus"]
    host = prom_endpoint["host"]
    port = prom_endpoint["port"]

    prom_url = f'http://{host}:{port}/api/v1/query_range'
    log.info(f'prometheus shard url: {prom_url}')
    return prom_url


def get_unsharded_prom_url() -> str:
    cm = get_config_manager()

    # e.g. titusprometheus.us-east-1.staging01cell001.test.netflix.net
    default_host = f'titusprometheus.{cm.get_region()}.{cm.get_stack()}.{cm.get_environment()}.netflix.net'
    host = cm.get_cached_str(PROMETHEUS_HOST_OVERRIDE, default_host)
    return f'http://{host}/api/v1/query_range'


@cached(cache = TTLCache(maxsize = 10, ttl = 60))
def get_prom_url() -> str:
    cm = get_config_manager()
    if cm.get_cached_bool(PROMETHEUS_SHARDING_ENABLED, DEFAULT_PROMETHEUS_SHARDING_ENABLED):
        return get_sharded_prom_url()
    else:
        return get_unsharded_prom_url()


class PrometheusResourceUsageProvider(ResourceUsageProvider):

    def __init__(self):
        self.__instance_id = get_config_manager().get_instance()

    def get_resource_usages(self, workload_ids: List[str]) -> List[ResourceUsage]:
        now = datetime.utcnow()
        end = dt2str(now)
        start = dt2str(now - timedelta(hours=1, minutes=2))

        usages = self.__get_resource(CPU_USAGE, workload_ids, start, end, 0.000000001)  # scale nanoseconds to seconds
        usages += self.__get_resource(MEM_USAGE, workload_ids, start, end)
        usages += self.__get_resource(NET_RECV_USAGE, workload_ids, start, end)
        usages += self.__get_resource(NET_TRANS_USAGE, workload_ids, start, end)
        usages += self.__get_resource(DISK_USAGE, workload_ids, start, end)
        return usages

    def __get_resource(self, resource: str, workload_ids: List[str], start: str, end: str, scale: float = 1.0) -> List[ResourceUsage]:
        ids = '|'.join(workload_ids)
        query = query_format[resource].format(self.__instance_id, ids)
        return self.__get_usages(query, resource, start, end, scale)

    def __get_usages(self, query: str, resource: str, start: str, end: str, scale: float = 1.0) -> List[ResourceUsage]:
        log.info('Getting Prometheus URL...')
        prom_url = get_prom_url()
        log.info(f'Prometheus URL: {prom_url}')

        resp = requests.get(
            prom_url,
            timeout=1,
            params={
                'query': query,
                'start': start,
                'end': end,
                'step': "1m"
            })

        if resp.status_code != 200:
            log.error("Failed to query prometheus. query: %s, status: %s, text: %s", query, resp.status_code, resp.text)
            return []

        return self._parse_prom_response(resource, resp.json(), scale)

    @staticmethod
    def __validate_prom_response(resp) -> bool:
        if "data" not in resp:
            log.error("Unexpected Prometheus response.  No 'data' field in response")
            return False

        data = resp["data"]
        if "result" not in data:
            log.error("Unexpected Prometheus response.  No 'result' field in data")
            return False

        result = data["result"]
        if len(result) == 0:
            log.warning("Empty result returned by Prometheus")
            return False

        return True

    @staticmethod
    def __validate_result(result) -> bool:
        if "metric" not in result:
            log.error("'metric' not defined in Prometheus result")
            return False

        metric = result["metric"]
        if "v3_job_titus_netflix_com_task_id" not in metric:
            log.error("task id not present in Prometheus metric")
            return False

        if "values" not in result:
            log.error("no values reported for Prometheus metric")
            return False

        values = result["values"]
        if len(values) == 0:
            log.error("empty values reported for Prometheus metric")
            return False

        return True

    def _parse_prom_response(self, resource: str, resp: dict, scale: float = 1.0) -> List[ResourceUsage]:
        # {
        # 	"status": "success",
        # 	"data": {
        # 		"resultType": "matrix",
        # 		"result": [{
        # 			"metric": {
        # 				"instance": "i-abc123",
        # 				"job": "agent-otel-ml-pipeline",
        # 				"v3_job_titus_netflix_com_task_id": "3d5fba95-f03a-4444-ab30-42d18db971bd"
        # 			},
        # 			"values": [
        # 				[1604698494.296, "999971618.6610168"],
        #               ...
        # 				[1604702094.296, "999987869.0338982"]
        # 			]
        # 		}, {
        # 			"metric": {
        # 				"instance": "i-abc123",
        # 				"job": "agent-otel-ml-pipeline",
        # 				"v3_job_titus_netflix_com_task_id": "9c711bbe-3ae7-4698-9b1f-b79751007a5e"
        # 			},
        # 			"values": [
        # 				[1604698494.296, "1000025560.2711865"],
        #               ...
        # 				[1604702094.296, "1000042929.4406779"]
        # 			]
        # 		}]
        # 	}
        # }
        if not self.__validate_prom_response(resp):
            return []

        usages = []
        results = resp["data"]["result"]
        for r in results:
            if not self.__validate_result(r):
                continue

            task_id = r["metric"]["v3_job_titus_netflix_com_task_id"]
            raw_values = r["values"]
            start_ts = raw_values[0][0]
            values = [float(ts_val[1]) * scale for ts_val in raw_values]

            usages.append(ResourceUsage(task_id, resource, start_ts, 60, values))

        return usages