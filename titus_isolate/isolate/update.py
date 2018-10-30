import logging

from titus_isolate.docker.constants import BURST
from titus_isolate.model.processor.utils import get_workload_ids

log = logging.getLogger()


def get_updates(cur_cpu, new_cpu):
    updates = {}
    for workload_id in get_workload_ids(new_cpu):
        new_thread_ids = __get_threads(new_cpu, workload_id)
        cur_thread_ids = __get_threads(cur_cpu, workload_id)
        if set(new_thread_ids) != set(cur_thread_ids):
            log.info("workload: '{}' updated threads from: '{}' to: '{}'".format(workload_id, cur_thread_ids, new_thread_ids))
            updates[workload_id] = new_thread_ids

    cur_empty_thread_ids = [t.get_id() for t in cur_cpu.get_empty_threads()]
    new_empty_thread_ids = [t.get_id() for t in new_cpu.get_empty_threads()]
    if set(cur_empty_thread_ids) != set(new_empty_thread_ids):
        updates[BURST] = new_empty_thread_ids

    return updates


def __get_threads(cpu, workload_id):
    return [t.get_id() for t in cpu.get_threads() if t.get_workload_id() == workload_id]
