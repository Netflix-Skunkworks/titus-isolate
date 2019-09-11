from typing import Union, List

from titus_isolate.config.constants import OPPORTUNISTIC_SHARES_SCALE_KEY, DEFAULT_OPPORTUNISTIC_SHARES_SCALE, \
    DEFAULT_SHARES_SCALE, DEFAULT_QUOTA_SCALE
from titus_isolate.isolate.update import _get_threads
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload import Workload, deserialize_workload
from titus_isolate.utils import get_config_manager

WORKLOAD_ID_KEY = "workload_id"
CPU_QUOTA_KEY = "cpu_quota"
CPU_SHARES_KEY = "cpu_shares"
CPU_THREAD_IDS_KEY = "cpu_thread_ids"


class WorkloadAllocateResponse:

    def __init__(self, workload_id: str, thread_ids: List[int], cpu_shares: int, cpu_quota: int):
        self.__workload_id = workload_id
        self.__thread_ids = thread_ids
        self.__cpu_shares = cpu_shares
        self.__cpu_quota = cpu_quota

    def get_workload_id(self):
        return self.__workload_id

    def get_cpu_quota(self) -> int:
        return self.__cpu_quota

    def get_cpu_shares(self) -> int:
        return self.__cpu_shares

    def get_thread_ids(self) -> List[int]:
        return self.__thread_ids

    def to_dict(self):
        return {
            WORKLOAD_ID_KEY: self.get_workload_id(),
            CPU_QUOTA_KEY: self.get_cpu_quota(),
            CPU_SHARES_KEY: self.get_cpu_shares(),
            CPU_THREAD_IDS_KEY: self.get_thread_ids()
        }


def get_cpu_quota(workload: Workload) -> int:
    if workload.is_burst():
        return -1

    return workload.get_thread_count() * DEFAULT_QUOTA_SCALE


def get_cpu_shares(workload: Workload) -> int:
    if workload.is_opportunistic():
        opportunistic_shares_scale = get_config_manager().get_int(
            OPPORTUNISTIC_SHARES_SCALE_KEY, DEFAULT_OPPORTUNISTIC_SHARES_SCALE)
        return workload.get_thread_count() * opportunistic_shares_scale

    return workload.get_thread_count() * DEFAULT_SHARES_SCALE


def get_workload_response(workload: Workload, cpu: Cpu) -> WorkloadAllocateResponse:
    thread_ids = _get_threads(cpu, workload.get_id())
    cpu_shares = get_cpu_shares(workload)
    cpu_quota = get_cpu_quota(workload)
    return WorkloadAllocateResponse(workload.get_id(), thread_ids, cpu_shares, cpu_quota)


def deserialize_workload_response(body):
    return WorkloadAllocateResponse(
        workload_id=body[WORKLOAD_ID_KEY],
        thread_ids=body[CPU_THREAD_IDS_KEY],
        cpu_shares=body[CPU_SHARES_KEY],
        cpu_quota=body[CPU_QUOTA_KEY])
