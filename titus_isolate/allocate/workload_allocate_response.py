from typing import Union, List

from titus_isolate.config.constants import OPPORTUNISTIC_SHARES_SCALE_KEY, DEFAULT_OPPORTUNISTIC_SHARES_SCALE, \
    DEFAULT_SHARES_SCALE, DEFAULT_QUOTA_SCALE
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_config_manager


class WorkloadAllocateResponse:

    def __init__(self, workload: Workload, thread_ids: List[int]):
        self.__workload = workload
        self.__thread_ids = thread_ids
        self.__cpu_shares = self.__get_shares(workload)
        self.__cpu_quota = self.__get_quota(workload)

    def get_workload(self):
        return self.__workload

    def get_cpu_quota(self) -> Union[int, None]:
        return self.__cpu_quota

    def get_cpu_shares(self) -> int:
        return self.__cpu_shares

    def get_thread_ids(self) -> List[int]:
        return self.__thread_ids

    @staticmethod
    def __get_quota(workload: Workload):
        if workload.is_burst():
            return -1

        return workload.get_thread_count() * DEFAULT_QUOTA_SCALE

    @staticmethod
    def __get_shares(workload: Workload):
        if workload.is_opportunistic():
            opportunistic_shares_scale = get_config_manager().get_int(
                OPPORTUNISTIC_SHARES_SCALE_KEY, DEFAULT_OPPORTUNISTIC_SHARES_SCALE)
            return workload.get_thread_count() * opportunistic_shares_scale

        return workload.get_thread_count() * DEFAULT_SHARES_SCALE
