from datetime import datetime, timedelta
from typing import List

import requests

from titus_isolate import log
from titus_isolate.allocate.constants import CPU_USAGE
from titus_isolate.config.constants import PROMETHEUS_HOST_OVERRIDE
from titus_isolate.monitor.resource_usage import ResourceUsage
from titus_isolate.monitor.resource_usage_provider import ResourceUsageProvider
from titus_isolate.utils import get_config_manager


query_format = {
    'cpu': 'rate(titus_cpu_cpuacct_usage{{instance="{}",v3_job_titus_netflix_com_task_id=~"{}"}}[1m])'
}


def dt2str(dt: datetime) -> str:
    return dt.isoformat("T") + "Z"


def get_prom_url() -> str:
    cm = get_config_manager()

    # e.g. titusprometheus.us-east-1.staging01cell001.test.netflix.net
    default_host = f'titusprometheus.{cm.get_region()}.{cm.get_stack()}.{cm.get_environment()}.netflix.net'
    host = cm.get_cached_str(PROMETHEUS_HOST_OVERRIDE, default_host)
    return f'http://{host}/api/v1/query_range'


class PrometheusResourceUsageProvider(ResourceUsageProvider):

    def __init__(self):
        self.__prom_url = get_prom_url()
        log.info(f'Prometheus URL: {self.__prom_url}')
        self.__instance_id = get_config_manager().get_instance()

    def get_resource_usages(self, workload_ids: List[str]) -> List[ResourceUsage]:
        now = datetime.utcnow()
        end = dt2str(now)
        start = dt2str(now - timedelta(hours=1, minutes=2))

        return self._get_cpu(workload_ids, start, end)

    def _get_cpu(self, workload_ids: List[str], start: str, end: str) -> List[ResourceUsage]:
        ids = '|'.join(workload_ids)
        cpu_query = query_format['cpu'].format(self.__instance_id, ids)
        return self.__get_usages(cpu_query, CPU_USAGE, start, end, 0.000000001)  # scale nanoseconds to seconds

    def __get_usages(self, query: str, type_name: str, start: str, end: str, scale: float = 1.0) -> List[ResourceUsage]:
        resp = requests.get(
            self.__prom_url,
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

        return self._parse_prom_response(type_name, resp.json(), scale)

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

    def _parse_prom_response(self, resource_name: str, resp: dict, scale: float = 1.0) -> List[ResourceUsage]:
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

            usages.append(ResourceUsage(task_id, resource_name, start_ts, 60, values))

        return usages
