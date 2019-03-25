import requests

from titus_isolate.allocate.cpu_allocate_exception import CpuAllocationException
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.utils import get_threads_body, parse_cpu, get_rebalance_body
from titus_isolate.config.constants import REMOTE_ALLOCATOR_URL
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.utils import get_config_manager


class RemoteCpuAllocator(CpuAllocator):
    def __init__(self, free_thread_provider):
        self.__url = get_config_manager().get(REMOTE_ALLOCATOR_URL, "http://localhost:7501")
        self.__headers = {'Content-Type': "application/json"}
        self.__reg = None

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        url = "{}/assign_threads".format(self.__url)
        body = get_threads_body(cpu, workload_id, workloads)
        response = requests.put(url, json=body, headers=self.__headers)

        if response.status_code == 200:
            return parse_cpu(response.json())

        raise CpuAllocationException("Failed to assign threads: {}".format(response.text))

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        url = "{}/free_threads".format(self.__url)
        body = get_threads_body(cpu, workload_id, workloads)
        response = requests.put(url, json=body, headers=self.__headers)

        if response.status_code == 200:
            return parse_cpu(response.json())

        raise CpuAllocationException("Failed to free threads: {}".format(response.text))

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        url = "{}/rebalance".format(self.__url)
        body = get_rebalance_body(cpu, workloads)
        response = requests.put(url, json=body, headers=self.__headers)

        if response.status_code == 200:
            return parse_cpu(response.json())

        raise CpuAllocationException("Failed to rebalance threads: {}".format(response.text))

    def set_registry(self, registry):
        pass

    def report_metrics(self, tags):
        pass
