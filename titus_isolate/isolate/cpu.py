from collections import defaultdict

from titus_isolate.model.processor.utils import get_emptiest_core, is_cpu_full
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_logger

import time

from titus_optimize.compute import optimize_ip

log = get_logger()

class IntegerProgramCpuAllocator:

    def __init__(self, cpu):
        self.__cpu = cpu
        self.__workload_insertion_times = {}
        self.__cache = {}  # TODO: use @functools.lru_cache instead

        curr_ids_per_workload = self.__cpu.get_workload_ids_to_thread_ids()
        if len(curr_ids_per_workload) > 0:
            log.warn("CPU already has assigned workloads.")
            for wid in curr_ids_per_workload.keys():
                # arbitrary ordering
                self.__workload_insertion_times[wid] = time.time()

    def get_cpu(self):
        return self.__cpu

    def __ordered_workload_ids(self):
        return [t[0] for t in sorted(self.__workload_insertion_times.items(), key=lambda t: t[1])]

    def __assign_new_mapping(self, thread_id2workload_id):
        self.__cpu.clear()
        for t in self.__cpu.get_threads():
            wid = thread_id2workload_id.get(t.get_id(), None)
            if wid is not None:
                t.claim(wid)

    def __compute_new_placement(self, current_placement, requested_units):
        key_req = '-'.join([str(e) for e in requested_units])
        cache_key = key_req
        if current_placement is not None: 
            cache_key += '&' + '%'.join(['|'.join([str(e) for e in v]) for v in current_placement])

        placement = self.__cache.get(cache_key, None)
        if placement is None:
            placement = optimize_ip(requested_units,
                            len(self.__cpu.get_threads()),
                            len(self.__cpu.get_packages()),
                            current_placement,
                            verbose=False)
            self.__cache[cache_key] = placement
        return placement


    def assign_threads(self, workload):
        """
        Use the integer -program solver to find the optimal static placement
        when adding the given workload on the cpu.

        `workload_insertion_times` is a workload_id --> integer dict
        indicating unix timestamps at which workloads currently running on the cpu
        have been placed.
        """
        n_compute_units = len(self.__cpu.get_threads())

        curr_ids_per_workload = self.__cpu.get_workload_ids_to_thread_ids()

        ordered_workload_ids = self.__ordered_workload_ids().copy()
        tid_2order = {i: t.get_id() for i, t in enumerate(self.__cpu.get_threads())}

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
        requested_cus += [workload.get_thread_count()]

        new_placement_vectors = self.__compute_new_placement(curr_placement_vectors, requested_cus)

        ordered_workload_ids.append(workload.get_id())

        thread_id2workload_id = {}
        for w_ind, v in enumerate(new_placement_vectors):
            for i, e in enumerate(v):
                if e == 1:
                    thread_id2workload_id[tid_2order[i]] = ordered_workload_ids[w_ind]

        self.__assign_new_mapping(thread_id2workload_id)
        self.__workload_insertion_times[workload.get_id()] = time.time()


    def free_threads(self, workload_id):
        """
        Use the integerprogram solver to find the optimal static placement
        after removing the given workload from the cpu.
        """
        n_compute_units = len(self.__cpu.get_threads())

        curr_ids_per_workload = self.__cpu.get_workload_ids_to_thread_ids()

        if workload_id not in curr_ids_per_workload:
            raise Exception("workload_id=`%s` is not placed on the instance. Cannot free it." % (workload_id,))

        ordered_workload_ids = self.__ordered_workload_ids()
        tid_2order = {i: t.get_id() for i, t in enumerate(self.__cpu.get_threads())}

        curr_placement_vectors = []
        for wid in ordered_workload_ids:
            cids = curr_ids_per_workload[wid]
            v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
            curr_placement_vectors.append(v)
        if len(curr_placement_vectors) == 0:
            raise Exception("Cannot free a workload from an empty CPU")

        requested_cus = [len(curr_ids_per_workload[wid]) if wid != workload_id else 0 for wid in ordered_workload_ids]

        new_placement_vectors = self.__compute_new_placement(curr_placement_vectors, requested_cus)

        thread_id2workload_id = {}
        for w_ind, v in enumerate(new_placement_vectors):
            if ordered_workload_ids[w_ind] == workload_id:
                continue
            for i, e in enumerate(v):
                if e == 1:
                    thread_id2workload_id[tid_2order[i]] = ordered_workload_ids[w_ind]

        self.__assign_new_mapping(thread_id2workload_id)
        self.__workload_insertion_times.pop(workload_id)


class GreedyCpuAllocator:

    def __init__(self, cpu):
        self.__cpu = cpu

    def get_cpu(self):
        return self.__cpu

    def assign_threads(self, workload):
        thread_count = workload.get_thread_count()
        claimed_threads = []

        if thread_count == 0:
            return claimed_threads

        log.info("Assigning '{}' thread(s) to workload: '{}'".format(workload.get_thread_count(), workload.get_id()))

        if is_cpu_full(self.__cpu):
            raise ValueError("Cannot assign workload: '{}' to full CPU.".format(workload.get_id()))

        package = self.__cpu.get_emptiest_package()

        while thread_count > 0 and len(package.get_empty_threads()) > 0:
            core = get_emptiest_core(package)
            empty_threads = core.get_empty_threads()[:thread_count]

            for empty_thread in empty_threads:
                log.debug("Claiming package:core:thread '{}:{}:{}' for workload '{}'".format(
                    package.get_id(), core.get_id(), empty_thread.get_id(), workload.get_id()))
                empty_thread.claim(workload.get_id())
                claimed_threads.append(empty_thread)
                thread_count -= 1

        return claimed_threads + self.assign_threads(Workload(workload.get_id(), thread_count, workload.get_type()))


    def free_threads(self, workload_id):
        for t in self.__cpu.get_threads():
            if t.get_workload_id() == workload_id:
                t.free()