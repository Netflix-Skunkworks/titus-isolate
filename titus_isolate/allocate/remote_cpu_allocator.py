import requests

from titus_isolate import log
from titus_isolate.allocate.constants import UNKNOWN_CPU_ALLOCATOR
from titus_isolate.allocate.cpu_allocate_exception import CpuAllocationException
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.utils import get_threads_body, parse_cpu, get_rebalance_body
from titus_isolate.config.constants import REMOTE_ALLOCATOR_URL, MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME
from titus_isolate.metrics.event_log_manager import EventLogManager
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.utils import get_config_manager


class RemoteCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider):
        config_manager = get_config_manager()

        self.__url = config_manager.get_str(REMOTE_ALLOCATOR_URL, "http://localhost:7501")
        self.__solver_max_runtime_secs = config_manager.get_float(MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME)
        self.__headers = {'Content-Type': "application/json"}
        self.__reg = None

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict) -> Cpu:
        url = "{}/assign_threads".format(self.__url)
        body = get_threads_body(cpu, workload_id, workloads, cpu_usage)
        log.debug("url: {}, body: {}".format(url, body))
        response = requests.put(url, json=body, headers=self.__headers, timeout=self.__solver_max_runtime_secs)
        log.debug("assign_threads response code: {}".format(response.status_code))

        if response.status_code == 200:
            return parse_cpu(response.json())

        raise CpuAllocationException("Failed to assign threads: {}".format(response.text))

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict) -> Cpu:
        url = "{}/free_threads".format(self.__url)
        body = get_threads_body(cpu, workload_id, workloads, cpu_usage)
        log.debug("url: {}, body: {}".format(url, body))
        response = requests.put(url, json=body, headers=self.__headers, timeout=self.__solver_max_runtime_secs)
        log.debug("free_threads response code: {}".format(response.status_code))

        if response.status_code == 200:
            return parse_cpu(response.json())

        raise CpuAllocationException("Failed to free threads: {}".format(response.text))

    def rebalance(self, cpu: Cpu, workloads: dict, cpu_usage: dict) -> Cpu:
        url = "{}/rebalance".format(self.__url)
        body = get_rebalance_body(cpu, workloads, cpu_usage)
        log.debug("url: {}, body: {}".format(url, body))
        response = requests.put(url, json=body, headers=self.__headers, timeout=self.__solver_max_runtime_secs)
        log.debug("rebalance response code: {}".format(response.status_code))

        if response.status_code == 200:
            return parse_cpu(response.json())

        raise CpuAllocationException("Failed to rebalance threads: {}".format(response.text))

    def get_name(self) -> str:
        url = "{}/cpu_allocator".format(self.__url)
        try:
            response = requests.get(url, timeout=1)
            return "Remote:{}".format(response.text)
        except:
            log.exception("Failed to GET cpu allocator name.")
            return UNKNOWN_CPU_ALLOCATOR

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass

    def set_event_log_manager(self, event_log_manager: EventLogManager):
        pass
