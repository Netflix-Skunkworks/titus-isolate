import logging

from titus_isolate.model.processor.utils import get_emptiest_core, is_cpu_full
from titus_isolate.model.workload import Workload

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


def assign_threads(cpu, workload):
    thread_count = workload.get_thread_count()
    claimed_threads = []

    if thread_count == 0:
        return claimed_threads

    log.info("Assigning '{}' thread(s) to workload: '{}'".format(workload.get_thread_count(), workload.get_id()))

    if is_cpu_full(cpu):
        raise ValueError("Cannot assign workload: '{}' to full CPU.", workload.get_id())

    package = cpu.get_emptiest_package()

    while thread_count > 0 and len(package.get_empty_threads()) > 0:
        core = get_emptiest_core(package)
        empty_threads = core.get_empty_threads()[:thread_count]

        for empty_thread in empty_threads:
            log.info("Claiming package:core:thread '{}:{}:{}' for workload '{}'".format(
                package.get_id(), core.get_id(), empty_thread.get_id(), workload.get_id()))
            empty_thread.claim(workload.get_id())
            claimed_threads.append(empty_thread)
            thread_count -= 1

    return claimed_threads + assign_threads(cpu, Workload(workload.get_id(), thread_count))


def free_threads(cpu, workload_id):
    freed_threads = []
    for t in cpu.get_threads():
        if t.get_workload_id() == workload_id:
            t.free()
            freed_threads.append(t)

    return freed_threads
