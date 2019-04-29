from titus_isolate import log
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.constants import RECONCILIATION_FAILURE_EXIT
from titus_isolate.exit_handler import ExitHandler
from titus_isolate.metrics.constants import RECONCILE_SKIP_COUNT, RECONCILE_SUCCESS_COUNT
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu


class Reconciler(MetricsReporter):

    def __init__(self, cgroup_manager: CgroupManager, exit_handler: ExitHandler):
        self.__cgroup_manager = cgroup_manager
        self.__exit_handler = exit_handler
        self.__reg = None
        self.__skip_count = 0
        self.__success_count = 0

    def reconcile(self, cpu: Cpu):
        if self.__cgroup_manager.has_pending_work():
            log.warning("Skipping reconciliation as some isolation work is still pending.")
            self.__skip_count += 1
            return

        workloads = self.get_workloads(cpu)
        for w_id, t_ids in workloads.items():
            cpuset = sorted(self.__cgroup_manager.get_cpuset(w_id))
            t_ids = sorted(t_ids)

            if cpuset != t_ids:
                log.error("Reconciliation has failed for workload: '{}', cpuset: {} != t_ids: {}".format(
                    w_id, cpuset, t_ids))
                self.__exit_handler.exit(RECONCILIATION_FAILURE_EXIT)
            else:
                log.info("Reconciliation has succeeded for workload: '{}', cpuset: {} == t_ids: {}".format(
                    w_id, cpuset, t_ids))

        self.__success_count += 1

    def get_skip_count(self):
        return self.__skip_count

    def get_success_count(self):
        return self.__success_count

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(RECONCILE_SKIP_COUNT, tags).set(self.get_skip_count())
        self.__reg.gauge(RECONCILE_SUCCESS_COUNT, tags).set(self.get_success_count())

    @staticmethod
    def get_workloads(cpu: Cpu):
        workloads = {}
        for t in cpu.get_threads():
            for w_id in t.get_workload_ids():
                if w_id in workloads:
                    workloads[w_id].append(t.get_id())
                else:
                    workloads[w_id] = [t.get_id()]

        return workloads
