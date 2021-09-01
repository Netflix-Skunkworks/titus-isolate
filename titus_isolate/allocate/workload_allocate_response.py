from typing import List, Optional

from titus_isolate.config.constants import DEFAULT_SHARES_SCALE, DEFAULT_QUOTA_SCALE, TITUS_ISOLATE_MEMORY_MIGRATE, \
    DEFAULT_TITUS_ISOLATE_MEMORY_MIGRATE, \
    TITUS_ISOLATE_MEMORY_SPREAD_PAGE, DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_PAGE, TITUS_ISOLATE_MEMORY_SPREAD_SLAB, \
    DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_SLAB
from titus_isolate.isolate.update import get_threads
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.workload_interface import Workload
from titus_isolate.utils import get_config_manager

WORKLOAD_ID_KEY = "workload_id"
CPU_QUOTA_KEY = "cpu_quota"
CPU_SHARES_KEY = "cpu_shares"
CPU_THREAD_IDS_KEY = "cpu_thread_ids"
MEMORY_MIGRATE = "memory_migrate"
MEMORY_SPREAD_PAGE = "memory_spread_page"
MEMORY_SPREAD_SLAB = "memory_spread_slab"


class WorkloadAllocateResponse:

    def __init__(self,
                 workload_id: str,
                 thread_ids: List[int],
                 cpu_shares: int,
                 cpu_quota: int,
                 memory_migrate: bool,
                 memory_spread_page: bool,
                 memory_spread_slab: bool):
        self.__workload_id = workload_id
        self.__thread_ids = thread_ids
        self.__cpu_shares = cpu_shares
        self.__cpu_quota = cpu_quota
        self.__memory_migrate = memory_migrate
        self.__memory_spread_page = memory_spread_page
        self.__memory_spread_slab = memory_spread_slab

    def get_workload_id(self) -> str:
        return self.__workload_id

    def get_cpu_quota(self) -> int:
        return self.__cpu_quota

    def get_cpu_shares(self) -> int:
        return self.__cpu_shares

    def get_thread_ids(self) -> List[int]:
        return self.__thread_ids

    def get_memory_migrate(self) -> bool:
        return self.__memory_migrate

    def get_memory_spread_page(self) -> bool:
        return self.__memory_spread_page

    def get_memory_spread_slab(self) -> bool:
        return self.__memory_spread_slab

    def to_dict(self):
        return {
            WORKLOAD_ID_KEY: self.get_workload_id(),
            CPU_QUOTA_KEY: self.get_cpu_quota(),
            CPU_SHARES_KEY: self.get_cpu_shares(),
            CPU_THREAD_IDS_KEY: self.get_thread_ids(),
            MEMORY_MIGRATE: self.get_memory_migrate(),
            MEMORY_SPREAD_PAGE: self.get_memory_spread_page(),
            MEMORY_SPREAD_SLAB: self.get_memory_spread_slab()
        }

    def __eq__(self, other):
        if other is None:
            return False

        return other.get_workload_id() == self.get_workload_id() and \
               other.get_cpu_quota() == self.get_cpu_quota() and \
               other.get_cpu_shares() == self.get_cpu_shares() and \
               set(other.get_thread_ids()) == set(self.get_thread_ids()) and \
               other.get_memory_migrate() == self.get_memory_migrate() and \
               other.get_memory_spread_page() == self.get_memory_spread_page() and \
               other.get_memory_spread_slab() == self.get_memory_spread_slab()


def get_cpu_quota(workload: Workload) -> int:
    return workload.get_thread_count() * DEFAULT_QUOTA_SCALE


def get_cpu_shares(workload: Workload) -> int:
    return workload.get_thread_count() * DEFAULT_SHARES_SCALE


def get_workload_response(workload: Workload, cpu: Cpu) -> Optional[WorkloadAllocateResponse]:
    thread_ids = get_threads(cpu, workload.get_id())
    cpu_shares = get_cpu_shares(workload)
    cpu_quota = get_cpu_quota(workload)

    if len(thread_ids) < 1:
        return None

    memory_migrate = DEFAULT_TITUS_ISOLATE_MEMORY_MIGRATE
    memory_spread_page = DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_PAGE
    memory_spread_slab = DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_SLAB

    config_manager = get_config_manager()
    if config_manager is not None:
        memory_migrate = config_manager.get_cached_bool(
            TITUS_ISOLATE_MEMORY_MIGRATE,
            DEFAULT_TITUS_ISOLATE_MEMORY_MIGRATE)
        memory_spread_page = config_manager.get_cached_bool(
            TITUS_ISOLATE_MEMORY_SPREAD_PAGE,
            DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_PAGE)
        memory_spread_slab = config_manager.get_cached_bool(
            TITUS_ISOLATE_MEMORY_SPREAD_SLAB,
            DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_SLAB)

    return WorkloadAllocateResponse(
        workload_id=workload.get_id(),
        thread_ids=thread_ids,
        cpu_shares=cpu_shares,
        cpu_quota=cpu_quota,
        memory_migrate=memory_migrate,
        memory_spread_page=memory_spread_page,
        memory_spread_slab=memory_spread_slab)


def deserialize_workload_response(body):
    return WorkloadAllocateResponse(
        workload_id=body[WORKLOAD_ID_KEY],
        thread_ids=body[CPU_THREAD_IDS_KEY],
        cpu_shares=body[CPU_SHARES_KEY],
        cpu_quota=body[CPU_QUOTA_KEY],
        memory_migrate=body.get(MEMORY_MIGRATE, DEFAULT_TITUS_ISOLATE_MEMORY_MIGRATE),
        memory_spread_page=body.get(MEMORY_SPREAD_PAGE, DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_PAGE),
        memory_spread_slab=body.get(MEMORY_SPREAD_SLAB, DEFAULT_TITUS_ISOLATE_MEMORY_SPREAD_SLAB))
