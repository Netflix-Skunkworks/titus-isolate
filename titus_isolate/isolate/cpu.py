import logging
from functools import reduce

from titus_isolate.model.workload import Workload

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


def assign_threads(cpu, workload):
    log.info("Assigning '{}' thread(s) to workload: '{}'".format(workload.get_thread_count(), workload.get_id()))

    thread_count = workload.get_thread_count()
    package = cpu.get_emptiest_package()

    while thread_count > 0 and len(package.get_empty_threads()) > 0:
        core = package.get_emptiest_core()
        empty_threads = core.get_empty_threads()[:thread_count]

        for empty_thread in empty_threads:
            log.info("Claiming package:core:thread '{}:{}:{}' for workload '{}'".format(
                package.get_id(), core.get_id(), empty_thread.get_id(), workload.get_id()))
            empty_thread.claim(workload.get_id())
            thread_count -= 1

    # We have exhausted capacity in the current package
    if thread_count > 0:
        assign_threads(cpu, Workload(workload.get_id(), thread_count))


def get_threads(cpu, workload):
    threads = reduce(list.__add__, [package.get_threads() for package in cpu.get_packages()])
    return [thread for thread in threads if thread.get_workload_id() == workload.get_id()]
