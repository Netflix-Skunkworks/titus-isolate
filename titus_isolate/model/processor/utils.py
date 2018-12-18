from functools import reduce

from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread

DEFAULT_PACKAGE_COUNT = 2
DEFAULT_CORE_COUNT = 4
DEFAULT_THREAD_COUNT = 2
DEFAULT_TOTAL_THREAD_COUNT = DEFAULT_PACKAGE_COUNT * DEFAULT_CORE_COUNT * DEFAULT_THREAD_COUNT


def get_empty_threads(threads):
    return [t for t in threads if not t.is_claimed()]


def get_emptiest_core(package):
    emptiest_core = package.get_cores()[0]
    curr_empty_thread_count = len(emptiest_core.get_empty_threads())

    for core in package.get_cores()[1:]:
        new_empty_thread_count = len(core.get_empty_threads())
        if new_empty_thread_count > curr_empty_thread_count:
            emptiest_core = core
            curr_empty_thread_count = new_empty_thread_count

    return emptiest_core


def is_cpu_full(cpu):
    empty_threads = reduce(list.__add__, [p.get_empty_threads() for p in cpu.get_packages()])
    return len(empty_threads) == 0


# Workloads
def get_workload_ids(cpu):
    return set([thread.get_workload_id() for thread in cpu.get_threads() if thread.is_claimed()])


def get_packages_with_workload(cpu, workload_id):
    return [package for package in cpu.get_packages() if is_on_package(package, workload_id)]


def is_on_package(package, workload_id):
    return len(get_threads_with_workload(package, workload_id)) > 0


def get_threads_with_workload(core, workload_id):
    return [thread for thread in core.get_threads() if thread.get_workload_id() == workload_id]


def visualize(cpu):
    """
    This function will return a string representing the current layout of
    workloads on the given cpu. Example:

    | a | c | b | b |   a: job1
    | b | c | d | d |   b: job2
    | ------------- |   c: job3
    | e | e | e | e |   d: job4
    | e | e | e | e |   e: job5

    In this example, there are 5 workloads, layed out on 2 sockets, each with 4 physical cores.
    Workload with id=`job3` is using the 2 hyperthreads of the 2nd core of the first socket.
    """
    buffer = []

    n_packages = len(cpu.get_packages())
    n_compute_units = len(cpu.get_threads())
    n_cus_per_package = n_compute_units // n_packages

    def get_str_repr(ind):
        res = ''
        while ind >= 0:
            res += chr(ord('a') + (ind % 26))
            ind -= 26
        return res

    workload_ids = []

    for ind_p, package in enumerate(cpu.get_packages()):
        S1 = [' '] * (n_cus_per_package // 2)
        S2 = [' '] * (n_cus_per_package // 2)

        j = 0
        for core in package.get_cores():
            threads = core.get_threads()
            for t in threads:
                if not t.is_claimed():
                    j += 1
                    continue
                wid = t.get_workload_id()
                if wid in workload_ids:
                    simple_id = workload_ids.index(wid)
                else:
                    workload_ids.append(wid)
                    simple_id = len(workload_ids) - 1
                if j % 2 == 0:
                    S1[j // 2] = get_str_repr(simple_id)
                else:
                    S2[j // 2] = get_str_repr(simple_id)
                j +=1
        buffer.append('| ' + ' | '.join(S1) + ' |\n')
        buffer.append('| ' + ' | '.join(S2) + ' |\n')
        if ind_p < n_packages - 1:
            buffer.append('| ' + '-' * len(' | '.join(S1)) + ' |\n')
    lgrid = len(buffer[0])
    for simple_id, wid in enumerate(workload_ids):
        if simple_id < len(buffer):
            buffer[simple_id] = buffer[simple_id][:-1] + '   %s: %s\n' % (get_str_repr(simple_id), wid)
        else:
            buffer.append(' ' * lgrid + '  %s: %s\n' % (get_str_repr(simple_id), wid))
    return ''.join(buffer)
