import copy
from threading import Thread, Lock, RLock

from titus_isolate import log
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.cgroup.utils import set_cpuset, wait_for_files, get_cpuset, parse_cpuset
from titus_isolate.config.constants import WAIT_CGROUP_FILE_KEY, WAIT_JSON_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC, \
    DEFAULT_WAIT_JSON_FILE_SEC
from titus_isolate.metrics.constants import WRITE_CPUSET_FAILED_KEY, WRITE_CPUSET_SUCCEEDED_KEY, \
    ISOLATED_WORKLOAD_COUNT, CPUSET_THREAD_COUNT
from titus_isolate.utils import get_config_manager, get_workload_manager


class FileCgroupManager(CgroupManager):

    def __init__(self):
        self.__reg = None
        self.__lock = Lock()
        self.__write_count = 0
        self.__fail_count = 0
        self.__isolated_workload_ids = set([])
        self.__thread_lock = RLock()
        self.__threads = []

    def set_cpuset(self, container_name, thread_ids):
        with self.__thread_lock:
            t = Thread(target=self.__set_cpuset, args=[container_name, thread_ids])
            t.start()
            self.__threads.append(t)
            self.__remove_dead_threads()

    def get_cpuset(self, container_name):
        cpuset_str = self.__get_cpuset(container_name)
        if cpuset_str is None:
            return []
        else:
            return parse_cpuset(cpuset_str)

    def release_cpuset(self, container_name):
        with self.__lock:
            self.__isolated_workload_ids.discard(container_name)

    def get_isolated_workload_ids(self):
        with self.__lock:
            wm = get_workload_manager()
            if wm is None:
                return set([])

            workloads = wm.get_workloads()
            workload_ids = set([w.get_id() for w in workloads])
            self.__isolated_workload_ids = self.__isolated_workload_ids.intersection(workload_ids)
            return copy.deepcopy(self.__isolated_workload_ids)

    def has_pending_work(self):
        with self.__thread_lock:
            return self.__get_thread_count() > 0

    def __get_thread_count(self) -> int:
        with self.__thread_lock:
            self.__remove_dead_threads()
            return len(self.__threads)

    def __remove_dead_threads(self):
        with self.__thread_lock:
            self.__threads = [t for t in self.__threads if t.is_alive()]

    def __set_cpuset(self, container_name, thread_ids):
        thread_ids_str = self.__get_thread_ids_str(thread_ids)

        try:
            self.__wait_for_files(container_name)
            log.info("updating workload: '{}' to cpuset.cpus: '{}'".format(container_name, thread_ids_str))
            set_cpuset(container_name, thread_ids_str)
            self.__write_succeeded(container_name)
        except:
            self.__write_failed()
            log.exception("Failed to apply cpuset to threads: '{}' for workload: '{}'".format(
                thread_ids_str, container_name))

    def __get_cpuset(self, container_name: str) -> str:
        try:
            self.__wait_for_files(container_name)
            log.info("getting cpuset.cpus for workload: '{}'".format(container_name))
            return get_cpuset(container_name)
        except:
            log.exception("Failed to read cpuset for workload: '{}'".format(container_name))
            return None

    def __write_succeeded(self, container_name):
        with self.__lock:
            self.__isolated_workload_ids.add(container_name)
            self.__write_count += 1

    def __write_failed(self):
        with self.__lock:
            self.__fail_count += 1

    @staticmethod
    def __get_thread_ids_str(thread_ids):
        return ",".join([str(t_id) for t_id in thread_ids])

    @staticmethod
    def __wait_for_files(container_name):
        cgroup_file_wait_timeout = get_config_manager().get_float(WAIT_CGROUP_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC)
        json_file_wait_timeout = get_config_manager().get_float(WAIT_JSON_FILE_KEY, DEFAULT_WAIT_JSON_FILE_SEC)
        wait_for_files(container_name, cgroup_file_wait_timeout, json_file_wait_timeout)

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(WRITE_CPUSET_SUCCEEDED_KEY, tags).set(self.__write_count)
        self.__reg.gauge(WRITE_CPUSET_FAILED_KEY, tags).set(self.__fail_count)
        self.__reg.gauge(ISOLATED_WORKLOAD_COUNT, tags).set(len(self.get_isolated_workload_ids()))
        self.__reg.gauge(CPUSET_THREAD_COUNT, tags).set(self.__get_thread_count())
