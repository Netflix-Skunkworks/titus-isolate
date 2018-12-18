from collections import defaultdict

from titus_isolate.model.processor.utils import get_emptiest_core, is_cpu_full
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_logger

from titus_optimize.compute import optimize_ip

log = get_logger()


def assign_threads(cpu, workload, workload_insertion_times={}):
    """
    Use the integer -program solver to find the optimal static placement
    when adding the given workload on the cpu.
    """
    n_packages = len(cpu.get_packages())
    n_compute_units = len(cpu.get_threads())

    curr_ids_per_workload = defaultdict(list)

    for t in cpu.get_threads():
        if t.is_claimed():
            curr_ids_per_workload[t.get_workload_id()] = curr_ids_per_workload[t.get_workload_id()] + [t.get_id()]

    if len(set(curr_ids_per_workload.keys()) ^ set(workload_insertion_times)) != 0:
        raise Exception("Invalid workload_insertion_times passed: `%s`" % (workload_insertion_times,))

    ordered_workload_ids = [t[0] for t in sorted(workload_insertion_times.items(), key=lambda t: t[1])]
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
    requested_cus += [workload.get_thread_count()]

    new_placement_vectors = optimize_ip(requested_cus, n_compute_units, n_packages, curr_placement_vectors, verbose=True)

    ordered_workload_ids.append(workload.get_id())

    thread_id2workload_id = {}
    for w_ind, v in enumerate(new_placement_vectors):
        for i, e in enumerate(v):
            if e == 1:
                thread_id2workload_id[tid_2order[i]] = ordered_workload_ids[w_ind]

    cpu.clear()

    new_used_threads = []
    for t in cpu.get_threads():
        wid = thread_id2workload_id.get(t.get_id(), None)
        if wid is not None:
            t.claim(wid)
            if wid == workload.get_id():
                new_used_threads.append(t)

    return new_used_threads


def free_threads(cpu, workload_id, workload_insertion_times={}):
    """
    Use the integerprogram solver to find the optimal static placement
    after removing the given workload from the cpu.
    """
    n_packages = len(cpu.get_packages())
    n_compute_units = len(cpu.get_threads())

    curr_ids_per_workload = defaultdict(list)

    for t in cpu.get_threads():
        if t.is_claimed():
            curr_ids_per_workload[t.get_workload_id()] = curr_ids_per_workload[t.get_workload_id()] + [t.get_id()]

    if workload_id not in curr_ids_per_workload:
        raise Exception("workload_id=`%s` is not placed on the instance. Cannot free it." % (workload_id,))
    if len(set(curr_ids_per_workload.keys()) ^ set(workload_insertion_times)) != 0:
        raise Exception("Invalid workload_insertion_times passed: `%s`" % (workload_insertion_times,))

    ordered_workload_ids = [t[0] for t in sorted(workload_insertion_times.items(), key=lambda t: t[1])]
    tid_2order = {i: t.get_id() for i, t in enumerate(cpu.get_threads())}

    curr_placement_vectors = []
    for wid in ordered_workload_ids:
        cids = curr_ids_per_workload[wid]
        v = [1 if tid_2order[i] in cids else 0 for i in range(n_compute_units)]
        curr_placement_vectors.append(v)
    if len(curr_placement_vectors) == 0:
        raise Exception("Cannot free a workload from an empty CPU")

    requested_cus = [len(curr_ids_per_workload[wid]) if wid != workload_id else 0 for wid in ordered_workload_ids]

    new_placement_vectors = optimize_ip(requested_cus, n_compute_units, n_packages, curr_placement_vectors, verbose=True)

    thread_id2workload_id = {}
    for w_ind, v in enumerate(new_placement_vectors):
        if ordered_workload_ids[w_ind] == workload_id:
            continue
        for i, e in enumerate(v):
            if e == 1:
                thread_id2workload_id[tid_2order[i]] = ordered_workload_ids[w_ind]

    cpu.clear()

    new_used_threads = []
    for t in cpu.get_threads():
        wid = thread_id2workload_id.get(t.get_id(), None)
        if wid is not None:
            t.claim(wid)
            new_used_threads.append(t)

    return new_used_threads
