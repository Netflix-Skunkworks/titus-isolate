from datetime import datetime as dt
from collections import defaultdict
import time

from titus_optimize.compute_v2 import IP_SOLUTION_TIME_BOUND, optimize_ip, IPSolverParameters

from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import ALPHA_NU, DEFAULT_ALPHA_NU, ALPHA_LLC, DEFAULT_ALPHA_LLC, ALPHA_L12, \
    DEFAULT_ALPHA_L12, ALPHA_ORDER, DEFAULT_ALPHA_ORDER, ALPHA_PREV, DEFAULT_ALPHA_PREV, \
    MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME, \
    RELATIVE_MIP_GAP_STOP, DEFAULT_RELATIVE_MIP_GAP_STOP, MIP_SOLVER, DEFAULT_MIP_SOLVER
from titus_isolate.metrics.constants import IP_ALLOCATOR_TIMEBOUND_COUNT, FORECAST_REBALANCE_FAILURE_COUNT
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.utils import get_burst_workloads, release_all_threads
from titus_isolate.model.utils import get_sorted_workloads
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider
from titus_isolate.predict.cpu_usage_predictor import PredEnvironment
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager


class CUVector:
    def __init__(
            self,
            requested_cus,
            curr_placement_vectors,
            ordered_workload_ids):
        self.requested_cus = requested_cus
        self.curr_placement_vectors_static = curr_placement_vectors
        self.ordered_workload_ids = ordered_workload_ids

    def __str__(self):
        return str(vars(self))


class ForecastIPCpuAllocator(CpuAllocator):

    def __init__(self,
                 cpu_usage_predictor_manager: CpuUsagePredictorManager,
                 config_manager: ConfigManager,
                 free_thread_provider: FreeThreadProvider):
        self.__reg = None
        self.__time_bound_call_count = 0
        self.__rebalance_failure_count = 0
        self.__ip_solver_params = IPSolverParameters(
            alpha_nu=config_manager.get_float(ALPHA_NU, DEFAULT_ALPHA_NU),
            alpha_llc=config_manager.get_float(ALPHA_LLC, DEFAULT_ALPHA_LLC),
            alpha_l12=config_manager.get_float(ALPHA_L12, DEFAULT_ALPHA_L12),
            alpha_order=config_manager.get_float(ALPHA_ORDER, DEFAULT_ALPHA_ORDER),
            alpha_prev=config_manager.get_float(ALPHA_PREV, DEFAULT_ALPHA_PREV))

        self.__solver_max_runtime_secs = config_manager.get_float(MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME)
        self.__solver_name = config_manager.get_str(MIP_SOLVER, DEFAULT_MIP_SOLVER)
        self.__solver_mip_gap = config_manager.get_float(RELATIVE_MIP_GAP_STOP, DEFAULT_RELATIVE_MIP_GAP_STOP)
        self.__cpu_usage_predictor_manager = cpu_usage_predictor_manager
        self.__config_manager = config_manager
        self.__free_thread_provider = free_thread_provider
        self.__cnt_rebalance_calls = 0
        self.__call_meta = None  # track things __place_threads call

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        self.__call_meta = {}
        cpu = request.get_cpu()
        cpu_usage = request.get_cpu_usage()
        workloads = request.get_workloads()
        workload_id = request.get_workload_id()
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        return AllocateResponse(
            self.__compute_allocation(cpu, workload_id, workloads, curr_ids_per_workload, cpu_usage, True),
            self.get_name(),
            self.__call_meta)

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        self.__call_meta = {}
        cpu = request.get_cpu()
        cpu_usage = request.get_cpu_usage()
        workloads = request.get_workloads()
        workload_id = request.get_workload_id()
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        if workload_id not in curr_ids_per_workload:
            raise Exception("workload_id=`%s` is not placed on the instance. Cannot free it." % (workload_id,))

        return AllocateResponse(
            self.__compute_allocation(cpu, workload_id, workloads, curr_ids_per_workload, cpu_usage, False),
            self.get_name(),
            self.__call_meta)

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        self.__call_meta = {}
        cpu = request.get_cpu()
        cpu_usage = request.get_cpu_usage()
        workloads = request.get_workloads()
        self.__cnt_rebalance_calls += 1

        if len(workloads) == 0:
            log.warning("Ignoring rebalance of empty CPU.")
            self.__call_meta['rebalance_empty'] = 1
            return AllocateResponse(cpu, self.get_name(), self.__call_meta)

        log.info("Rebalancing with predictions...")
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        return AllocateResponse(
            self.__compute_allocation(cpu, None, workloads, curr_ids_per_workload, cpu_usage, None),
            self.get_name(),
            self.__call_meta)

    def __compute_allocation(self, cpu, workload_id, workloads, curr_ids_per_workload, cpu_usage, is_add):
        predicted_usage = self.__predict_usage(workloads, cpu_usage)
        cpu = self.__place_threads(cpu, workload_id, workloads, curr_ids_per_workload, predicted_usage, is_add)

        # Burst workload computation
        burst_workloads = get_burst_workloads(workloads.values())
        if not is_add:
            burst_workloads = [workload for workload in burst_workloads if workload.get_id() != workload_id]

        # Claim all free threads for burst workloads
        burst_workload_ids = [w.get_id() for w in burst_workloads]
        free_threads = self.__free_thread_provider.get_free_threads(cpu, workloads, predicted_usage)
        for t in free_threads:
            for w_id in burst_workload_ids:
                t.claim(w_id)

        return cpu

    def get_name(self) -> str:
        return self.__class__.__name__

    def __get_cpu_usage_predictor(self):
        return self.__cpu_usage_predictor_manager.get_predictor()

    def __predict_usage(self, workloads, cpu_usage):
        res = {}
        cpu_usage_predictor = self.__get_cpu_usage_predictor()

        cm = self.__config_manager
        pred_env = PredEnvironment(cm.get_region(), cm.get_environment(), dt.utcnow().hour)

        start_time = time.time()
        for w in workloads.values():  # TODO: batch the call
            pred = cpu_usage_predictor.predict(w, cpu_usage.get(w.get_id(), None), pred_env)
            res[w.get_id()] = pred
        stop_time = time.time()
        self.__call_meta['pred_cpu_usage_dur_secs'] = stop_time - start_time
        try:
            self.__call_meta['pred_cpu_usage_model_id'] = cpu_usage_predictor.get_model().meta_data['model_training_titus_task_id']
        except:
            self.__call_meta['pred_cpu_usage_model_id'] = 'unknown'

        log.info("Usage prediction per workload: " + str(res))
        if len(res) > 0:
            self.__call_meta['pred_cpu_usage'] = dict(res)
        return res

    def __place_threads(self, cpu, workload_id, workloads, curr_ids_per_workload, predicted_cpu_usage, is_add) -> Cpu:
        # this will predict against the new or deleted workload too if it's static
        cu_vector = self.__get_requested_cu_vector(cpu, workload_id, workloads, curr_ids_per_workload, is_add)

        cpu = self.__compute_apply_placement(
            cpu,
            cu_vector.requested_cus,
            cu_vector.curr_placement_vectors_static,
            predicted_cpu_usage,
            workloads,
            cu_vector.ordered_workload_ids)

        return cpu

    @staticmethod
    def __get_requested_cu_vector(cpu, workload_id, workloads, curr_ids_per_workload, is_add) -> CUVector:
        n_compute_units = len(cpu.get_threads())
        tid_2order = cpu.get_natural_indexing_2_original_indexing()

        ordered_workload_ids = [w.get_id() for w in get_sorted_workloads(workloads.values())]

        changed_workload = workloads.get(workload_id, None)

        curr_placement_vectors_static = []
        for wid in ordered_workload_ids:
            if (changed_workload is not None) and (wid == changed_workload.get_id()) and is_add:
                continue
            cids = curr_ids_per_workload[wid]
            v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
            curr_placement_vectors_static.append(v)

        is_remove = (not is_add) and workload_id in ordered_workload_ids

        if is_remove:
            requested_cus = [
                workloads[wid].get_thread_count()
                if wid != changed_workload.get_id() else 0
                for wid in ordered_workload_ids
            ]
        else:
            requested_cus = [
                workloads[wid].get_thread_count()
                for wid in ordered_workload_ids
            ]

        return CUVector(
            requested_cus,
            curr_placement_vectors_static if len(curr_placement_vectors_static) > 0 else None,
            ordered_workload_ids)

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
            curr_placement_vectors_static,
            predicted_usage_static,
            workloads,
            ordered_workload_ids_static):

        predicted_usage_static_vector = None
        if len(predicted_usage_static) > 0:
            predicted_usage_static_vector = [predicted_usage_static[w_id] for w_id in ordered_workload_ids_static]

        new_placement_vectors = self.__compute_new_placement(
            cpu,
            requested_cus,
            curr_placement_vectors_static,
            predicted_usage_static_vector)

        tid_2order = cpu.get_natural_indexing_2_original_indexing()
        thread_id2workload_ids = defaultdict(list)

        for w_ind, v in enumerate(new_placement_vectors):
            for i, e in enumerate(v):
                if e == 1:
                    thread_id2workload_ids[tid_2order[i]].append(ordered_workload_ids_static[w_ind])

        release_all_threads(cpu, workloads.values())
        self.__assign_new_mapping(cpu, thread_id2workload_ids)

        # TODO: log what's in print_statistics of compute_v2
        return cpu

    def __compute_new_placement(
            self,
            cpu,
            requested_units,
            current_placement,
            predicted_usage):

        num_threads = len(cpu.get_threads())
        ip_params = self.__ip_solver_params
        log.info("Using solver: {}".format(self.__solver_name))

        num_packages = len(cpu.get_packages())

        sparse_prev_alloc = None
        if current_placement is not None:
            sparse_prev_alloc = [[i for i, e in enumerate(v) if e == 1] for v in current_placement]

        use_per_workload = None
        if predicted_usage is not None:
            use_per_workload = predicted_usage

        self.__call_meta['ip_solver_call_args'] = {
            "req_units": [int(e) for e in requested_units],
            "num_threads": num_threads,
            "num_packages": num_packages
        }

        if sparse_prev_alloc is not None:
            self.__call_meta['ip_solver_call_args']['previous_allocation'] = sparse_prev_alloc
        if use_per_workload is not None:
            self.__call_meta['ip_solver_call_args']['use_per_workload'] = use_per_workload

        try:
            start_time = time.time()
            placement, status = optimize_ip(
                requested_units,
                num_threads,
                num_packages,
                previous_allocation=current_placement,
                use_per_workload=predicted_usage,
                solver_params=ip_params,
                verbose=False,
                max_runtime_secs=self.__solver_max_runtime_secs,
                mip_gap=self.__solver_mip_gap,
                solver=self.__solver_name)
            stop_time = time.time()
            self.__call_meta['ip_solver_call_dur_secs'] = stop_time - start_time
            self.__call_meta['ip_success'] = 1

            if status == IP_SOLUTION_TIME_BOUND:
                self.__time_bound_call_count += 1

        except Exception as e:
            self.__call_meta['ip_success'] = 0
            raise e

        return placement

    def set_solver_max_runtime_secs(self, val):
        self.__solver_max_runtime_secs = val

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(IP_ALLOCATOR_TIMEBOUND_COUNT, tags).set(self.__time_bound_call_count)
        self.__reg.gauge(FORECAST_REBALANCE_FAILURE_COUNT, tags).set(self.__rebalance_failure_count)
