from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.config.constants import DEFAULT_MAX_SOLVER_RUNTIME, MAX_SOLVER_RUNTIME
from titus_isolate.utils import get_config_manager
from titus_optimize.compute import IP_SOLUTION_TIME_BOUND, optimize_ip

from titus_isolate.event.constants import STATIC
from titus_isolate.metrics.constants import IP_ALLOCATOR_TIMEBOUND_COUNT
from titus_isolate.model.processor.utils import is_cpu_full
from titus_isolate.model.utils import get_sorted_workloads, get_burst_workloads, release_all_threads, \
    update_burst_workloads, rebalance
from titus_isolate.monitor.empty_free_thread_provider import EmptyFreeThreadProvider


class IntegerProgramCpuAllocator(CpuAllocator):

    def __init__(self, free_thread_provider=EmptyFreeThreadProvider()):

        self.__reg = None
        self.__cache = {}
        self.__time_bound_call_count = 0

        self.__solver_max_runtime_secs = get_config_manager().get_float(MAX_SOLVER_RUNTIME, DEFAULT_MAX_SOLVER_RUNTIME)
        self.__free_thread_provider = free_thread_provider

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workloads = request.get_workloads()
        workload_id = request.get_workload_id()

        burst_workloads = get_burst_workloads(workloads.values())
        release_all_threads(cpu, burst_workloads)
        if workloads[workload_id].get_type() == STATIC:
            self.__assign_threads(cpu, workload_id, workloads)
        update_burst_workloads(cpu, workloads, self.__free_thread_provider)

        return AllocateResponse(cpu, self.get_name())

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workloads = request.get_workloads()
        workload_id = request.get_workload_id()

        burst_workloads = get_burst_workloads(workloads.values())
        release_all_threads(cpu, burst_workloads)
        if workloads[workload_id].get_type() == STATIC:
            self.__free_threads(cpu, workload_id, workloads)
        workloads.pop(workload_id)
        update_burst_workloads(cpu, workloads, self.__free_thread_provider)

        return AllocateResponse(cpu, self.get_name())

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        cpu = request.get_cpu()
        workloads = request.get_workloads()

        cpu = rebalance(cpu, workloads, self.__free_thread_provider)
        return AllocateResponse(cpu, self.get_name())

    def get_name(self) -> str:
        return self.__class__.__name__

    def __assign_threads(self, cpu, workload_id, workloads):
        """
        Use the integer-program solver to find the optimal static placement
        when adding the given workload on the cpu.

        `workload_insertion_times` is a workload_id --> integer dict
        indicating unix timestamps at which workloads currently running on the cpu
        have been placed.
        """

        if is_cpu_full(cpu):
            raise ValueError("CPU is full, failed to add workload: '{}'".format(workload_id))

        n_compute_units = len(cpu.get_threads())
        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        from titus_isolate.model.utils import get_sorted_workloads
        ordered_workload_ids = [w.get_id() for w in get_sorted_workloads(workloads.values())]
        tid_2order = {i: t.get_id() for i, t in enumerate(cpu.get_threads())}

        curr_placement_vectors = []
        for wid in ordered_workload_ids:
            cids = curr_ids_per_workload[wid]
            v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
            curr_placement_vectors.append(v)
        if len(curr_placement_vectors) == 0:
            curr_placement_vectors = None
            requested_cus = []
        else:
            requested_cus = [sum(v) for v in curr_placement_vectors]

        workload = workloads[workload_id]
        requested_cus += [workload.get_thread_count()]

        new_placement_vectors = self.__compute_new_placement(cpu, curr_placement_vectors, requested_cus)

        ordered_workload_ids.append(workload.get_id())

        thread_id2workload_id = {}
        for w_ind, v in enumerate(new_placement_vectors):
            for i, e in enumerate(v):
                if e == 1:
                    thread_id2workload_id[tid_2order[i]] = ordered_workload_ids[w_ind]

        self.__assign_new_mapping(cpu, thread_id2workload_id)

        return cpu

    def __free_threads(self, cpu, workload_id, workloads):
        """
        Use the integerprogram solver to find the optimal static placement
        after removing the given workload from the cpu.
        """

        n_compute_units = len(cpu.get_threads())

        curr_ids_per_workload = cpu.get_workload_ids_to_thread_ids()

        if workload_id not in curr_ids_per_workload:
            raise Exception("workload_id=`%s` is not placed on the instance. Cannot free it." % (workload_id,))

        ordered_workload_ids = [w.get_id() for w in get_sorted_workloads(workloads.values())]
        tid_2order = {i: t.get_id() for i, t in enumerate(cpu.get_threads())}

        curr_placement_vectors = []
        for wid in ordered_workload_ids:
            cids = curr_ids_per_workload[wid]
            v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
            curr_placement_vectors.append(v)
        if len(curr_placement_vectors) == 0:
            raise Exception("Cannot free a workload from an empty CPU")

        requested_cus = [len(curr_ids_per_workload[wid]) if wid != workload_id else 0 for wid in ordered_workload_ids]

        new_placement_vectors = self.__compute_new_placement(cpu, curr_placement_vectors, requested_cus)

        thread_id2workload_id = {}
        for w_ind, v in enumerate(new_placement_vectors):
            if ordered_workload_ids[w_ind] == workload_id:
                continue
            for i, e in enumerate(v):
                if e == 1:
                    thread_id2workload_id[tid_2order[i]] = ordered_workload_ids[w_ind]

        self.__assign_new_mapping(cpu, thread_id2workload_id)
        return cpu

    @staticmethod
    def __assign_new_mapping(cpu, thread_id2workload_id):
        cpu.clear()
        for t in cpu.get_threads():
            wid = thread_id2workload_id.get(t.get_id(), None)
            if wid is not None:
                t.claim(wid)

    def __compute_new_placement(self, cpu, current_placement, requested_units):
        key_req = '-'.join([str(e) for e in requested_units])
        cache_key = key_req
        if current_placement is not None:
            cache_key += '&' + '%'.join(['|'.join([str(e) for e in v]) for v in current_placement])

        cache_val = self.__cache.get(cache_key, None)
        if cache_val is None:
            placement, status = optimize_ip(
                requested_units,
                len(cpu.get_threads()),
                len(cpu.get_packages()),
                current_placement,
                verbose=False,
                max_runtime_secs=self.__solver_max_runtime_secs)
            self.__cache[cache_key] = (placement, status)
        else:
            placement, status = cache_val[0], cache_val[1]

        if status == IP_SOLUTION_TIME_BOUND:
            self.__time_bound_call_count += 1

        return placement

    def set_solver_max_runtime_secs(self, val):
        self.__solver_max_runtime_secs = val

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(IP_ALLOCATOR_TIMEBOUND_COUNT, tags).set(self.__time_bound_call_count)
