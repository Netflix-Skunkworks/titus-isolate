import requests

from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse, deserialize_response
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.constants import UNKNOWN_CPU_ALLOCATOR
from titus_isolate.allocate.cpu_allocate_exception import CpuAllocationException
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.config.constants import REMOTE_ALLOCATOR_URL, MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME, \
    MAX_SOLVER_CONNECT_SEC, DEFAULT_MAX_SOLVER_CONNECT_SEC
from titus_isolate.utils import get_config_manager


class RemoteCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider):
        config_manager = get_config_manager()

        self.__url = config_manager.get_str(REMOTE_ALLOCATOR_URL, "http://localhost:7501")
        solver_max_runtime_secs = config_manager.get_float(MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME)
        solver_max_connect_secs = config_manager.get_float(MAX_SOLVER_CONNECT_SEC, DEFAULT_MAX_SOLVER_CONNECT_SEC)
        self.__timeout = (solver_max_connect_secs, solver_max_runtime_secs)
        self.__headers = {'Content-Type': "application/json"}
        self.__reg = None

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        url = "{}/assign_threads".format(self.__url)
        body = request.to_dict()
        log.debug("url: {}, body: {}".format(url, body))
        response = requests.put(url, json=body, headers=self.__headers, timeout=self.__timeout)
        log.debug("assign_threads response code: {}".format(response.status_code))

        if response.status_code == 200:
            return deserialize_response(response.headers, response.json())

        raise CpuAllocationException("Failed to assign threads: {}".format(response.text))

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        url = "{}/free_threads".format(self.__url)
        body = request.to_dict()

        log.info("freeing threads remotely for workload: %s, url: %s", request.get_workload_id(), url)
        response = requests.put(url, json=body, headers=self.__headers, timeout=self.__timeout)
        log.info("freed threads remotely with response code: %s for workload: %s", response.status_code, request.get_workload_id())

        if response.status_code == 200:
            return deserialize_response(response.headers, response.json())

        raise CpuAllocationException("Failed to free threads: {}".format(response.text))

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        url = "{}/rebalance".format(self.__url)
        body = request.to_dict()
        log.debug("url: {}, body: {}".format(url, body))
        response = requests.put(url, json=body, headers=self.__headers, timeout=self.__timeout)
        log.debug("rebalance response code: {}".format(response.status_code))

        if response.status_code == 200:
            return deserialize_response(response.headers, response.json())

        raise CpuAllocationException("Failed to rebalance threads: {}".format(response.text))

    def get_name(self) -> str:
        url = "{}/cpu_allocator".format(self.__url)
        try:
            response = requests.get(url, timeout=self.__timeout)
            return "Remote({})".format(response.text)
        except Exception:
            log.exception("Failed to GET cpu allocator name.")
            return UNKNOWN_CPU_ALLOCATOR

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
