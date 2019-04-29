from typing import Dict

from titus_isolate.event.constants import BURST, STATIC
from titus_isolate.event.utils import get_container_name, get_cpu, get_mem, get_disk, get_network, get_workload_type, \
    get_image, get_app_name, get_job_type, get_owner_email, get_command, get_entrypoint
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.monitor.free_thread_provider import FreeThreadProvider


def get_workload_from_event(event):
    identifier = get_container_name(event)
    cpus = get_cpu(event)
    mem = get_mem(event)
    disk = get_disk(event)
    network = get_network(event)
    app_name = get_app_name(event)
    owner_email = get_owner_email(event)
    image = get_image(event)
    command = get_command(event)
    entrypoint = get_entrypoint(event)
    job_type = get_job_type(event)
    workload_type = get_workload_type(event)

    return Workload(
        identifier=identifier,
        thread_count=cpus,
        mem=mem,
        disk=disk,
        network=network,
        app_name=app_name,
        owner_email=owner_email,
        image=image,
        command=command,
        entrypoint=entrypoint,
        job_type=job_type,
        workload_type=workload_type)


def get_burst_workloads(workloads):
    return get_workloads_by_type(workloads, BURST)


def get_static_workloads(workloads):
    return get_workloads_by_type(workloads, STATIC)


def get_workloads_by_type(workloads, workload_type):
    return [w for w in workloads if w.get_type() == workload_type]


def get_sorted_workloads(workloads):
    return sorted(workloads, key=lambda w: w.get_creation_time())


def release_all_threads(cpu, workloads):
    for w in workloads:
        release_threads(cpu, w.get_id())


def release_threads(cpu, workload_id):
    for t in cpu.get_threads():
        t.free(workload_id)


def update_burst_workloads(cpu: Cpu, workload_map: Dict[str, Workload], free_thread_provider: FreeThreadProvider):
    free_threads = free_thread_provider.get_free_threads(cpu, workload_map)
    burst_workloads = get_burst_workloads(workload_map.values())
    if len(burst_workloads) == 0:
        return

    for t in free_threads:
        for w in burst_workloads:
            t.claim(w.get_id())


def rebalance(cpu: Cpu, workloads: dict, free_thread_provider: FreeThreadProvider) -> Cpu:
    burst_workloads = get_burst_workloads(workloads.values())
    release_all_threads(cpu, burst_workloads)
    update_burst_workloads(cpu, workloads, free_thread_provider)

    return cpu
