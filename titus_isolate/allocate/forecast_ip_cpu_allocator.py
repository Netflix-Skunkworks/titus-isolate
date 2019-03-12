from collections import defaultdict

from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_optimize.compute_v2 import IP_SOLUTION_TIME_BOUND, optimize_ip, IPSolverParameters

from titus_isolate.event.constants import STATIC
from titus_isolate.metrics.constants import IP_ALLOCATOR_TIMEBOUND_COUNT
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.utils import is_cpu_full
from titus_isolate.model.utils import get_sorted_workloads, get_burst_workloads, release_all_threads, \
    update_burst_workloads, rebalance
from titus_isolate.model.utils import get_sorted_workloads
from titus_isolate.utils import get_workload_monitor_manager


class ForecastIPCpuAllocator(CpuAllocator):

    def __init__(self, cpu_usage_predictor, solver_max_runtime_secs=5):
        self.__reg = None
        self.__time_bound_call_count = 0
        self.__ip_solver_params = IPSolverParameters()

        self.__solver_max_runtime_secs = solver_max_runtime_secs
        self.__cpu_usage_predictor = cpu_usage_predictor
        self.__cnt_rebalance_calls = 0

    def assign_threads(self, cpu : Cpu, workload_id, workloads) -> Cpu:
        if is_cpu_full(cpu):
            raise ValueError("CPU is full, failed to add workload: '{}'".format(workload_id))

        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        return self.__place_threads(cpu, workload_id, workloads, curr_ids_per_workload, True)

    def free_threads(self, cpu : Cpu, workload_id, workloads) -> Cpu:
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        if workload_id not in curr_ids_per_workload:
            raise Exception("workload_id=`%s` is not placed on the instance. Cannot free it." % (workload_id,))

        return self.__place_threads(cpu, workload_id, workloads, curr_ids_per_workload, False)

    def rebalance(self, cpu: Cpu, workloads: dict) -> Cpu:
        self.__cnt_rebalance_calls += 1
        if self.__cnt_rebalance_calls == 1000000:
            self.__cnt_rebalance_calls = 1

        if len(workloads) == 0:
            return cpu

        if (self.__cnt_rebalance_calls -1) % 10 == 0:
            # slow path, predict and adjust
            curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()
            return self.__place_threads(cpu, None, workloads, curr_ids_per_workload, None)
        else:
            # fast check if there is an issue?
            return cpu
    
    def __predict_usage_static(self, workloads, default_value=None) -> dict:
        res = {}
        if self.__cpu_usage_predictor is None:
            if default_value is None:
                return res
            for w in workloads.values():
                if w.get_type() == STATIC:
                    res[w.get_id()] = default_value
            return res

        wmm = get_workload_monitor_manager()
        cpu_usages = wmm.get_cpu_usage(3600)
        for w in workloads.values(): # TODO: batch the call
            if w.get_type() == STATIC:
                pred = self.__cpu_usage_predictor.predict(w, cpu_usages.get(w.get_id(), None))
                if default_value is not None and pred is None:
                    pred = default_value
                res[w.get_id()] = pred
        log.info("Usage prediction per workload: " + str(res))
        return res

    def __place_threads(self, cpu, workload_id, workloads, curr_ids_per_workload, is_add):
        # this will predict against the new or deleted workload too if it's static
        predicted_usage_static = self.__predict_usage_static(workloads)

        requested_cus, curr_placement_vectors_static, \
            ordered_workload_ids_static, ordered_workload_ids_burst, burst_pool_size_req = \
            self.__get_requested_cu_vector(
                cpu, workload_id, workloads, curr_ids_per_workload, is_add)

        # todo (maybe?) add burst pool current placement to curr_placement_vectors_static

        cpu = self.__compute_apply_placement(cpu, requested_cus, burst_pool_size_req,
            curr_placement_vectors_static, predicted_usage_static,
            workloads, ordered_workload_ids_static, ordered_workload_ids_burst)

        return cpu

    @staticmethod
    def __get_requested_cu_vector(cpu, workload_id, workloads, curr_ids_per_workload, is_add):
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
                requested_cus = [len(curr_ids_per_workload[wid]) if wid != changed_workload.get_id() else 0 for wid in ordered_workload_ids_static]
            else:
                requested_cus = [len(curr_ids_per_workload[wid]) for wid in ordered_workload_ids_static if (changed_workload is not None) and wid != changed_workload.get_id()]

        if (changed_workload is not None) and (changed_workload.get_type() == STATIC) and is_add:
            requested_cus += [changed_workload.get_thread_count()]

        burst_workloads = get_burst_workloads(workloads.values())
        burst_pool_size_req = sum([w.get_thread_count() for w in burst_workloads]) if len(burst_workloads) > 0 else 0

        return requested_cus, curr_placement_vectors_static, ordered_workload_ids_static, ordered_workload_ids_burst, burst_pool_size_req

    @staticmethod
    def __assign_new_mapping(cpu, thread_id2workload_ids):
        cpu.clear()
        for t in cpu.get_threads():
            wids = thread_id2workload_ids.get(t.get_id(), None)
            if wids is not None:
                for wi in wids:
                    t.claim(wi)

    def __compute_apply_placement(self, cpu, requested_cus, burst_pool_size_req,
            curr_placement_vectors_static, predicted_usage_static,
            workloads, ordered_workload_ids_static, ordered_workload_ids_burst):
        new_placement_vectors = self.__compute_new_placement(cpu, requested_cus, burst_pool_size_req,
        curr_placement_vectors_static, predicted_usage_static)

        new_placement_vectors_static = new_placement_vectors[:-1] if burst_pool_size_req != 0 else new_placement_vectors
        new_placement_vector_burst = new_placement_vectors[-1] if burst_pool_size_req != 0 else None

        tid_2order = cpu.get_natural_indexing_2_original_indexing()
        thread_id2workload_ids = defaultdict(list)

        #print(ordered_workload_ids_static)
        #print(requested_cus)
        #print(new_placement_vectors_static)
        #print(burst_pool_size_req)

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

        #print(cpu)
        # todo: log what's in print_statistics of compute_v2
        return cpu

    def __compute_new_placement(self, cpu, requested_units, burst_pool_size_req,
            current_placement, predicted_usage_static):
        placement, status = optimize_ip(
                requested_units,
                burst_pool_size_req,
                len(cpu.get_threads()),
                len(cpu.get_packages()),
                previous_allocation=current_placement,
                use_per_workload=predicted_usage_static if len(predicted_usage_static) > 0 else None,
                solver_params=self.__ip_solver_params,
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

