from titus_isolate import log
from titus_isolate.cgroup.cgroup_manager import CgroupManager
from titus_isolate.constants import RECONCILIATION_FAILURE_EXIT
from titus_isolate.exit_handler import ExitHandler
from titus_isolate.model.processor.cpu import Cpu


class Reconciler:

    def __init__(self, cgroup_manager: CgroupManager, exit_handler: ExitHandler):
        self.__cgroup_manager = cgroup_manager
        self.__exit_handler = exit_handler
        self.__unisolated_workload_count = 0
        self.__missing_cpuset_count = 0

    def reconcile(self, cpu: Cpu):
        workloads = self.get_workloads(cpu)
        for w_id, t_ids in workloads.items():
            isolated_workload_ids = self.__cgroup_manager.get_isolated_workload_ids()
            if w_id not in isolated_workload_ids:
                log.warn("Workload: '{}' is not in isolated set: '{}' so unable to retrieve cpuset during reconciliation.".format(w_id, isolated_workload_ids))
                self.__unisolated_workload_count += 1
                continue

            cpuset = self.__cgroup_manager.get_cpuset(w_id)
            if cpuset is None:
                log.warn("Workload likely exited during reconciliation: '{}'".format(w_id))
                self.__missing_cpuset_count += 1
                continue

            cpuset = sorted(cpuset)
            t_ids = sorted(t_ids)

            if cpuset != t_ids:
                log.error("Reconciliation has failed for workload: '{}', cpuset: {} != t_ids: {}".format(
                    w_id, cpuset, t_ids))
                self.__exit_handler.exit(RECONCILIATION_FAILURE_EXIT)
            else:
                log.info("Reconciliation has succeeded for workload: '{}', cpuset: {} == t_ids: {}".format(
                    w_id, cpuset, t_ids))

    def get_unisolated_workload_count(self):
        return self.__unisolated_workload_count

    def get_missing_cpuset_count(self):
        return self.__missing_cpuset_count

    def get_total_warning_count(self):
        return self.get_unisolated_workload_count() + self.get_missing_cpuset_count()

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
