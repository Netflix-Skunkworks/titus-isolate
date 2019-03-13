import json
from datetime import datetime as dt
from collections import defaultdict
import copy
from math import ceil, floor

from titus_optimize.compute_v2 import IP_SOLUTION_TIME_BOUND, optimize_ip, IPSolverParameters

from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.event.constants import STATIC
from titus_isolate.metrics.constants import IP_ALLOCATOR_TIMEBOUND_COUNT
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.utils import is_cpu_full
from titus_isolate.model.utils import get_burst_workloads, release_all_threads
from titus_isolate.model.utils import get_sorted_workloads
from titus_isolate.monitor.workload_monitor_manager import WorkloadMonitorManager
from titus_isolate.predict.cpu_usage_predictor import PredEnvironment
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager
from titus_isolate.utils import get_config_manager, get_workload_monitor_manager


class CUVector:
    def __init__(
            self,
            requested_cus,
            curr_placement_vectors_static,
            ordered_workload_ids_static,
            ordered_workload_ids_burst,
            burst_pool_size_req):

        self.requested_cus = requested_cus
        self.curr_placement_vectors_static = curr_placement_vectors_static
        self.ordered_workload_ids_static = ordered_workload_ids_static
        self.ordered_workload_ids_burst = ordered_workload_ids_burst
        self.burst_pool_size_req = burst_pool_size_req

    def to_dict(self):
        return {
            "requested_cus": self.requested_cus,
            "curr_placement_vectors_static": self.curr_placement_vectors_static,
            "ordered_workload_ids_static": [str(w_id) for w_id in self.ordered_workload_ids_static],
            "ordered_workload_ids_burst": [str(w_id) for w_id in self.ordered_workload_ids_burst],
            "burst_pool_size_req": self.burst_pool_size_req
        }

    def __str__(self):
        return json.dumps(self.to_dict())


class ForecastIPCpuAllocator(CpuAllocator):

    def __init__(self, cpu_usage_predictor_manager: CpuUsagePredictorManager, solver_max_runtime_secs: int = 5):
        self.__reg = None
        self.__time_bound_call_count = 0
        self.__ip_solver_params = IPSolverParameters()

        self.__solver_max_runtime_secs = solver_max_runtime_secs
        self.__cpu_usage_predictor_manager = cpu_usage_predictor_manager
        self.__cnt_rebalance_calls = 0

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        return self.__place_threads(cpu, workload_id, workloads, curr_ids_per_workload, True)

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict) -> Cpu:
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        if workload_id not in curr_ids_per_workload:
            raise Exception("workload_id=`%s` is not placed on the instance. Cannot free it." % (workload_id,))

        return self.__place_threads(cpu, workload_id, workloads, curr_ids_per_workload, False)

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        self.__cnt_rebalance_calls += 1

        if len(workloads) == 0:
            return cpu

        if (self.__cnt_rebalance_calls - 1) % 10 == 0:
            log.info("Rebalancing with predictions...")
            # slow path, predict and adjust
            curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()
            return self.__place_threads(cpu, None, workloads, curr_ids_per_workload, None)
        else:
            # fast check if there is an issue?
            return cpu

    def __get_cpu_usage_predictor(self):
        return self.__cpu_usage_predictor_manager.get_predictor()

    def __predict_usage_static(self, workloads, default_value=None) -> dict:
        res = {}
        cpu_usage_predictor = self.__get_cpu_usage_predictor()

        wmm: WorkloadMonitorManager = get_workload_monitor_manager()
        cm: ConfigManager = get_config_manager()
        pred_env = PredEnvironment(cm.get_region(), cm.get_environment(), dt.utcnow().hour)

        cpu_usages = wmm.get_cpu_usage(seconds=3600, agg_granularity_secs=60)

        for w in workloads.values():  # TODO: batch the call
            if w.get_type() == STATIC:
                pred = cpu_usage_predictor.predict(w, cpu_usages.get(w.get_id(), None), pred_env)
                if default_value is not None and pred is None:
                    pred = default_value
                res[w.get_id()] = pred
        log.info("Usage prediction per workload: " + str(res))
        return res

    def __place_threads(self, cpu, workload_id, workloads, curr_ids_per_workload, is_add):
        # this will predict against the new or deleted workload too if it's static
        predicted_usage_static = self.__predict_usage_static(workloads)
        cu_vector = self.__get_requested_cu_vector(cpu, workload_id, workloads, curr_ids_per_workload, is_add)

        # TODO: (maybe?) add burst pool current placement to curr_placement_vectors_static

        log.debug("workloads: {}".format(workloads.values()))
        log.debug("cu_vector: {}".format(cu_vector))
        log.debug("predicted_usage_static: {}".format(predicted_usage_static))

        cpu = self.__compute_apply_placement(
            cpu,
            cu_vector.requested_cus,
            cu_vector.burst_pool_size_req,
            cu_vector.curr_placement_vectors_static,
            predicted_usage_static,
            workloads,
            cu_vector.ordered_workload_ids_static,
            cu_vector.ordered_workload_ids_burst)

        return cpu

    @staticmethod
    def __get_requested_cu_vector(cpu, workload_id, workloads, curr_ids_per_workload, is_add) -> CUVector:
        n_compute_units = len(cpu.get_threads())
        tid_2order = cpu.get_natural_indexing_2_original_indexing()

        ordered_workload_ids_static = []
        ordered_workload_ids_burst = []
        for w in get_sorted_workloads(workloads.values()):
            if w.get_type() == STATIC:
                ordered_workload_ids_static.append(w.get_id())
            else:
                ordered_workload_ids_burst.append(w.get_id())

        changed_workload = workloads.get(workload_id, None)

        curr_placement_vectors_static = []
        for wid in ordered_workload_ids_static:
            if (changed_workload is not None) and (wid == changed_workload.get_id()):
                continue
            cids = curr_ids_per_workload[wid]
            v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
            curr_placement_vectors_static.append(v)
        if len(curr_placement_vectors_static) == 0:
            curr_placement_vectors_static = None
            requested_cus = []
        else:
            if (changed_workload is not None) and (changed_workload.get_type() == STATIC) and (not is_add):
                requested_cus = [len(curr_ids_per_workload[wid]) if wid != changed_workload.get_id() else 0 for wid in
                                 ordered_workload_ids_static]
            elif changed_workload is not None:
                requested_cus = [len(curr_ids_per_workload[wid]) for wid in ordered_workload_ids_static if
                                 wid != changed_workload.get_id()]
            else:
                requested_cus = [len(curr_ids_per_workload[wid]) for wid in ordered_workload_ids_static]

        if (changed_workload is not None) and (changed_workload.get_type() == STATIC) and is_add:
            requested_cus += [changed_workload.get_thread_count()]

        burst_workloads = get_burst_workloads(workloads.values())
        burst_pool_size_req = sum([w.get_thread_count() for w in burst_workloads]) if len(burst_workloads) > 0 else 0

        return CUVector(
            requested_cus,
            curr_placement_vectors_static,
            ordered_workload_ids_static,
            ordered_workload_ids_burst,
            burst_pool_size_req)

    @staticmethod
    def __assign_new_mapping(cpu, thread_id2workload_ids):
        cpu.clear()
        for t in cpu.get_threads():
            wids = thread_id2workload_ids.get(t.get_id(), None)
            if wids is not None:
                for wi in wids:
                    t.claim(wi)

    def __compute_apply_placement(
            self,
            cpu,
            requested_cus,
            burst_pool_size_req,
            curr_placement_vectors_static,
            predicted_usage_static,
            workloads,
            ordered_workload_ids_static,
            ordered_workload_ids_burst):

        new_placement_vectors = self.__compute_new_placement(
            cpu,
            requested_cus,
            burst_pool_size_req,
            curr_placement_vectors_static,
            predicted_usage_static)

        new_placement_vectors_static = new_placement_vectors[:-1] if burst_pool_size_req != 0 else new_placement_vectors
        new_placement_vector_burst = new_placement_vectors[-1] if burst_pool_size_req != 0 else None

        tid_2order = cpu.get_natural_indexing_2_original_indexing()
        thread_id2workload_ids = defaultdict(list)

        for w_ind, v in enumerate(new_placement_vectors_static):
            for i, e in enumerate(v):
                if e == 1:
                    thread_id2workload_ids[tid_2order[i]].append(ordered_workload_ids_static[w_ind])

        if new_placement_vector_burst is not None:
            for i, e in enumerate(new_placement_vector_burst):
                if e == 1:
                    for w_ind in ordered_workload_ids_burst:
                        thread_id2workload_ids[tid_2order[i]].append(w_ind)

        release_all_threads(cpu, workloads.values())
        self.__assign_new_mapping(cpu, thread_id2workload_ids)

        # TODO: log what's in print_statistics of compute_v2
        return cpu

    def __compute_new_placement(
            self,
            cpu,
            requested_units,
            burst_pool_size_req,
            current_placement,
            predicted_usage_static):

        num_threads = len(cpu.get_threads())

        ip_params = self.__ip_solver_params
        # if the instance is mostly empty, loosen constraint
        # on burst pool growth size
        num_req_static = sum(requested_units)
        if num_req_static < num_threads / 2 and burst_pool_size_req > 0:
            ip_params = copy.deepcopy(ip_params)
            th_num_cores_static = ceil(num_req_static)
            ip_params.max_burst_pool_increase_ratio = floor((num_threads - th_num_cores_static)/burst_pool_size_req)

        placement, status = optimize_ip(
            requested_units,
            burst_pool_size_req,
            num_threads,
            len(cpu.get_packages()),
            previous_allocation=current_placement,
            use_per_workload=predicted_usage_static if len(predicted_usage_static) > 0 else None,
            solver_params=ip_params,
            verbose=False,
            max_runtime_secs=self.__solver_max_runtime_secs)

        if status == IP_SOLUTION_TIME_BOUND:
            self.__time_bound_call_count += 1

        return placement

    def set_solver_max_runtime_secs(self, val):
        self.__solver_max_runtime_secs = val

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(IP_ALLOCATOR_TIMEBOUND_COUNT, tags).set(self.__time_bound_call_count)
