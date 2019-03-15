from titus_isolate import log
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider
from titus_isolate.utils import get_workload_monitor_manager


class ThresholdFreeThreadProvider(FreeThreadProvider):

    def __init__(
            self,
            total_threshold: float,
            total_duration_sec: int,
            per_workload_threshold: float,
            per_workload_duration_sec: int):

        self.__total_threshold = total_threshold
        self.__total_duration_sec = total_duration_sec

        self.__per_workload_threshold = per_workload_threshold
        self.__per_workload_duration_sec = per_workload_duration_sec

        log.debug("ThresholdFreeThreadProvider created with total_threshold: '{}', total_duration_sec: '{}', per_workload_threshold: '{}', per_workload_duration_sec: '{}'".format(
           self.__total_threshold, self.__total_duration_sec, self.__per_workload_threshold, self.__per_workload_duration_sec))

    def get_free_threads(self, cpu: Cpu) -> list:
        wmm = get_workload_monitor_manager()
        if wmm is None:
            log.debug("Workload monitor manager is not yet set.")
            return []

        total_usage = wmm.get_cpu_usage(self.__total_duration_sec, self.__total_duration_sec)
        workload_usage = wmm.get_cpu_usage(self.__per_workload_duration_sec, self.__per_workload_duration_sec)

        # A thread is free if no workload has claimed it or its combined usage is below the threshold
        free_threads = [t for t in cpu.get_threads() if self.__is_free(t, workload_usage, total_usage)]
        free_thread_ids = [t.get_id() for t in free_threads]
        log.debug("Found free threads: {}".format(free_thread_ids))

        return free_threads

    @staticmethod
    def __is_reporting_metrics(workload_id, usage_dicts: list) -> bool:
        for d in usage_dicts:
            if workload_id not in d:
                return False

            if d[workload_id] is None:
                return False

        return True

    def __is_free(self, thread: Thread, workload_usage: dict, total_usage: dict) -> bool:
        log.debug("Determining if thread: '{}' is free.".format(thread.get_id()))
        workload_ids = thread.get_workload_ids()

        # If no workload is using the thread, it's free.
        if len(workload_ids) == 0:
            return True

        # Check individual workloads to see if any is using the thread.
        for w_id in workload_ids:

            # A workload probably just started so the thread isn't free
            if not self.__is_reporting_metrics(w_id, [workload_usage, total_usage]):
                log.debug("Thread '{}' is not free because workload: '{}' is does not have usage metrics.".format(
                    thread.get_id(), w_id))
                return False

            usage = workload_usage[w_id][str(thread.get_id())]

            if usage > self.__per_workload_threshold:
                log.debug("Thread '{}' is not free because the cpu usage: '{}' of workload: '{}' exceeds the per-workload usage threshold: '{}'.".format(
                    thread.get_id(), usage, w_id, self.__per_workload_threshold))
                return False

        # If the cpu's total usage exceeds a threshold it's not free.
        aggregate_usage = self.__get_aggregate_usage(thread, total_usage)
        if aggregate_usage > self.__total_threshold:
            log.debug("Thread '{}' is not free because it's usage: '{}' exceeds the total thread usage threshold: '{}'."
                      .format(thread.get_id(), aggregate_usage, self.__total_threshold))
            return False

        log.debug("Thread '{}' is free.".format(thread.get_id()))
        return True

    def __get_aggregate_usage(self, thread: Thread, total_usage: dict) -> float:
        agg_usage = 0.0
        for w_id in thread.get_workload_ids():
            agg_usage += total_usage[w_id][str(thread.get_id())]

        return agg_usage
