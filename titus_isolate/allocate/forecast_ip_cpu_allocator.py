from datetime import datetime as dt
from collections import defaultdict
import copy
from math import ceil, floor
import time

from titus_optimize.compute_v2 import IP_SOLUTION_TIME_BOUND, optimize_ip, IPSolverParameters

from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import ALPHA_NU, DEFAULT_ALPHA_NU, ALPHA_LLC, DEFAULT_ALPHA_LLC, ALPHA_L12, \
    DEFAULT_ALPHA_L12, ALPHA_ORDER, DEFAULT_ALPHA_ORDER, ALPHA_PREV, DEFAULT_ALPHA_PREV, BURST_MULTIPLIER, \
    DEFAULT_BURST_MULTIPLIER, MAX_BURST_POOL_INCREASE_RATIO, DEFAULT_MAX_BURST_POOL_INCREASE_RATIO, \
    BURST_CORE_COLLOC_USAGE_THRESH, DEFAULT_BURST_CORE_COLLOC_USAGE_THRESH, WEIGHT_CPU_USE_BURST, \
    DEFAULT_WEIGHT_CPU_USE_BURST, MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME, \
    RELATIVE_MIP_GAP_STOP, DEFAULT_RELATIVE_MIP_GAP_STOP, MIP_SOLVER, DEFAULT_MIP_SOLVER
from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.metrics.constants import IP_ALLOCATOR_TIMEBOUND_COUNT, FORECAST_REBALANCE_FAILURE_COUNT
from titus_isolate.metrics.event_log_manager import EventLogManager
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.utils import get_burst_workloads, release_all_threads
from titus_isolate.model.utils import get_sorted_workloads
from titus_isolate.predict.cpu_usage_predictor import PredEnvironment
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager


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

    def __str__(self):
        return str(vars(self))


class ForecastIPCpuAllocator(CpuAllocator):

    def __init__(self,
                 cpu_usage_predictor_manager: CpuUsagePredictorManager,
                 config_manager: ConfigManager):
        self.__reg = None
        self.__time_bound_call_count = 0
        self.__rebalance_failure_count = 0
        self.__ip_solver_params = IPSolverParameters(
            alpha_nu=config_manager.get_float(ALPHA_NU, DEFAULT_ALPHA_NU),
            alpha_llc=config_manager.get_float(ALPHA_LLC, DEFAULT_ALPHA_LLC),
            alpha_l12=config_manager.get_float(ALPHA_L12, DEFAULT_ALPHA_L12),
            alpha_order=config_manager.get_float(ALPHA_ORDER, DEFAULT_ALPHA_ORDER),
            alpha_prev=config_manager.get_float(ALPHA_PREV, DEFAULT_ALPHA_PREV),
            burst_multiplier=config_manager.get_float(BURST_MULTIPLIER, DEFAULT_BURST_MULTIPLIER),
            max_burst_pool_increase_ratio=config_manager.get_float(MAX_BURST_POOL_INCREASE_RATIO, DEFAULT_MAX_BURST_POOL_INCREASE_RATIO),
            burst_core_colloc_usage_thresh=config_manager.get_float(BURST_CORE_COLLOC_USAGE_THRESH, DEFAULT_BURST_CORE_COLLOC_USAGE_THRESH),
            weight_cpu_use_burst=config_manager.get_float(WEIGHT_CPU_USE_BURST, DEFAULT_WEIGHT_CPU_USE_BURST))

        self.__solver_max_runtime_secs = config_manager.get_float(MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME)
        self.__solver_name = config_manager.get_str(MIP_SOLVER, DEFAULT_MIP_SOLVER)
        self.__solver_mip_gap = config_manager.get_float(RELATIVE_MIP_GAP_STOP, DEFAULT_RELATIVE_MIP_GAP_STOP)
        self.__cpu_usage_predictor_manager = cpu_usage_predictor_manager
        self.__config_manager = config_manager
        self.__cnt_rebalance_calls = 0
        self.__event_log_manager = None

    def assign_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict) -> Cpu:
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        cpu = self.__place_threads(cpu, workload_id, workloads, curr_ids_per_workload, cpu_usage, True)
        self.report_cpu_event(self.__event_log_manager, cpu, list(workloads.values()), cpu_usage)
        return cpu

    def free_threads(self, cpu: Cpu, workload_id: str, workloads: dict, cpu_usage: dict) -> Cpu:
        for t in cpu.get_claimed_threads():
            t.free(workload_id)
        self.report_cpu_event(self.__event_log_manager, cpu, list(workloads.values()), cpu_usage)
        return cpu

    def rebalance(self, cpu: Cpu, workloads: dict, cpu_usage: dict) -> Cpu:
        def __complete_rebalance():
            self.report_cpu_event(self.__event_log_manager, cpu, list(workloads.values()), cpu_usage)
            return cpu

        self.__cnt_rebalance_calls += 1

        if len(workloads) == 0:
            return __complete_rebalance()

        log.info("Rebalancing with predictions...")
        # slow path, predict and adjust
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        try:
            cpu = self.__place_threads(cpu, None, workloads, curr_ids_per_workload, cpu_usage, None)
            return __complete_rebalance()
        except:
            log.exception("Failed to rebalance, doing nothing.")
            self.__rebalance_failure_count += 1
            return __complete_rebalance()

    def get_name(self) -> str:
        return self.__class__.__name__

    def __get_cpu_usage_predictor(self):
        return self.__cpu_usage_predictor_manager.get_predictor()

    def __predict_usage(self, workloads, cpu_usage):
        res_static = {}
        res_burst = {}
        cpu_usage_predictor = self.__get_cpu_usage_predictor()

        cm = self.__config_manager
        pred_env = PredEnvironment(cm.get_region(), cm.get_environment(), dt.utcnow().hour)

        for w in workloads.values():  # TODO: batch the call
            pred = cpu_usage_predictor.predict(w, cpu_usage.get(w.get_id(), None), pred_env)
            if w.get_type() == STATIC:
                res_static[w.get_id()] = pred
            elif w.get_type() == BURST:
                res_burst[w.get_id()] = pred
        log.info("Usage prediction per static workload: " + str(res_static))
        log.info("Usage prediction per burst workload: " + str(res_burst))
        return res_static, res_burst

    def __place_threads(self, cpu, workload_id, workloads, curr_ids_per_workload, cpu_usage, is_add):
        # this will predict against the new or deleted workload too if it's static
        predicted_usage_static, predicted_usage_burst = self.__predict_usage(workloads, cpu_usage)
        cu_vector = self.__get_requested_cu_vector(cpu, workload_id, workloads, curr_ids_per_workload, is_add)

        cpu = self.__compute_apply_placement(
            cpu,
            cu_vector.requested_cus,
            cu_vector.burst_pool_size_req,
            cu_vector.curr_placement_vectors_static,
            predicted_usage_static,
            predicted_usage_burst,
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
            if (changed_workload is not None) and (wid == changed_workload.get_id()) and is_add:
                continue
            cids = curr_ids_per_workload[wid]
            v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
            curr_placement_vectors_static.append(v)

        requested_cus = [
            workloads[wid].get_thread_count()
            for wid in ordered_workload_ids_static]

        burst_workloads = get_burst_workloads(workloads.values())
        burst_pool_size_req = sum([w.get_thread_count() for w in burst_workloads]) if len(burst_workloads) > 0 else 0

        return CUVector(
            requested_cus,
            curr_placement_vectors_static if len(curr_placement_vectors_static) > 0 else None,
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
            predicted_usage_burst,
            workloads,
            ordered_workload_ids_static,
            ordered_workload_ids_burst):

        predicted_usage_static_vector = None
        if len(predicted_usage_static) > 0:
            predicted_usage_static_vector = [predicted_usage_static[w_id] for w_id in ordered_workload_ids_static]

        sum_burst_pred = 0.0
        if len(predicted_usage_burst) > 0:
            sum_burst_pred = sum(v for v in predicted_usage_burst.values())

        new_placement_vectors = self.__compute_new_placement(
            cpu,
            requested_cus,
            burst_pool_size_req,
            sum_burst_pred,
            curr_placement_vectors_static,
            predicted_usage_static_vector)

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
            sum_burst_pred,
            current_placement,
            predicted_usage_static):

        num_threads = len(cpu.get_threads())

        ip_params = self.__ip_solver_params
        if burst_pool_size_req > 0 and sum_burst_pred > 0:
            ip_params.weight_cpu_use_burst = sum_burst_pred / burst_pool_size_req

        # if the instance is mostly empty, loosen constraint
        # on burst pool growth size
        num_req_static = sum(requested_units)
        if num_req_static < num_threads / 2 and burst_pool_size_req > 0:
            ip_params = copy.deepcopy(ip_params)
            th_num_cores_static = ceil(num_req_static)
            ip_params.max_burst_pool_increase_ratio = floor((num_threads - th_num_cores_static) / burst_pool_size_req)

        log.info("Using solver: {}".format(self.__solver_name))

        num_packages = len(cpu.get_packages())

        logged_dict = {
            'ip_solver_call_args': {
                "requested_units": [int(e) for e in requested_units],
                "burst_pool_size_req": burst_pool_size_req,
                "num_threads": num_threads,
                "num_packages": num_packages,
                "previous_allocation": [[i for i, e in enumerate(v) if e == 1] for v in current_placement],
                "use_per_workload": predicted_usage_static,
                "weight_cpu_use_burst": ip_params.weight_cpu_use_burst,
                "max_burst_pool_incr_ratio": ip_params.max_burst_pool_increase_ratio
            }
        }

        try:
            start_time = time.time()
            placement, status = optimize_ip(
                requested_units,
                burst_pool_size_req,
                num_threads,
                num_packages,
                previous_allocation=current_placement,
                use_per_workload=predicted_usage_static,
                solver_params=ip_params,
                verbose=False,
                max_runtime_secs=self.__solver_max_runtime_secs,
                mip_gap=self.__solver_mip_gap,
                solver=self.__solver_name)
            stop_time = time.time()
            logged_dict['ip_solver_call_duration_secs'] = stop_time - start_time
            logged_dict['ip_success'] = 1

            if status == IP_SOLUTION_TIME_BOUND:
                self.__time_bound_call_count += 1
        except:
            logged_dict['ip_success'] = 0

        from titus_isolate.metrics.event_log import get_msg_ctx
        msg = get_msg_ctx()
        for k,v in logged_dict.items():
            msg['payload'][k] = v
        self.__event_log_manager.report_event(msg)

        return placement

    def set_solver_max_runtime_secs(self, val):
        self.__solver_max_runtime_secs = val

    def set_event_log_manager(self, event_log_manager: EventLogManager):
        self.__event_log_manager = event_log_manager

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(IP_ALLOCATOR_TIMEBOUND_COUNT, tags).set(self.__time_bound_call_count)
        self.__reg.gauge(FORECAST_REBALANCE_FAILURE_COUNT, tags).set(self.__rebalance_failure_count)
