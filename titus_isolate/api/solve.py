import datetime
from threading import Lock

from flask import Flask, request, jsonify

from titus_isolate import log
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload

lock = Lock()
cpu_allocator = None

app = Flask(__name__)


def get_cpu_allocator():
    with lock:
        global cpu_allocator
        return cpu_allocator


def set_cpu_allocator(allocator):
    with lock:
        global cpu_allocator
        cpu_allocator = allocator


def __get_cpu(body):
    return parse_cpu(body["cpu"])


def __get_workload_id(body):
    return body["workload_id"]


def __get_workloads(body):
    workloads = {}
    for w in [parse_workload(w_str) for w_str in body["workloads"]]:
        workloads[w.get_id()] = w

    return workloads


def get_threads_body(cpu: Cpu, workload_id: str, workloads: dict) -> dict:
    w_list = [w.to_dict() for w in workloads.values()]
    return {
        "cpu": cpu.to_dict(),
        "workload_id": workload_id,
        "workloads": w_list
    }


def get_rebalance_body(cpu: Cpu, workloads: dict) -> dict:
    w_list = [w.to_dict() for w in workloads.values()]
    return {
        "cpu": cpu.to_dict(),
        "workloads": w_list
    }


def get_threads_arguments(body):
    workload_id = __get_workload_id(body)
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    return cpu, workload_id, workloads


def get_rebalance_arguments(body):
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    return cpu, workloads


def parse_cpu(cpu_dict: dict) -> Cpu:
    packages = []
    for p in cpu_dict["packages"]:
        cores = []
        for c in p["cores"]:
            threads = []
            for t in c["threads"]:
                thread = Thread(t["id"])
                for w_id in t["workload_id"]:
                    thread.claim(w_id)
                threads.append(thread)
            cores.append(Core(c["id"], threads))
        packages.append(Package(p["id"], cores))

    return Cpu(packages)


def parse_workload(workload_dict: dict) -> Workload:

    workload = Workload(
        identifier=workload_dict['id'],
        thread_count=workload_dict['thread_count'],
        mem=workload_dict['mem'],
        disk=workload_dict['disk'],
        network=workload_dict['network'],
        app_name=workload_dict['app_name'],
        owner_email=workload_dict['owner_email'],
        image=workload_dict['image'],
        command=workload_dict['command'],
        entrypoint=workload_dict['entrypoint'],
        job_type=workload_dict['job_type'],
        workload_type=workload_dict['type'])

    # Input example:  "2019-03-23 18:03:50.668041"
    creation_time = datetime.datetime.strptime(workload_dict["creation_time"], '%Y-%m-%d %H:%M:%S.%f')
    workload.set_creation_time(creation_time)
    return workload


@app.route('/assign_threads', methods=['PUT'])
def assign_threads():
    allocator = get_cpu_allocator()

    if allocator is None:
        log.error("Cannot assign threads, CPU allocator is not set.")
        return "CPU allocator not set", 500

    try:
        body = request.get_json()
        cpu_in, workload_id, workloads = get_threads_arguments(body)
        cpu_out = allocator.assign_threads(cpu_in, workload_id, workloads)
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to assign threads")
        return "Failed to assign threads", 500


@app.route('/free_threads', methods=['PUT'])
def free_threads():
    allocator = get_cpu_allocator()

    if allocator is None:
        log.error("Cannot free threads, CPU allocator is not set.")
        return "CPU allocator not set", 500

    try:
        body = request.get_json()
        cpu_in, workload_id, workloads = get_threads_arguments(body)
        cpu_out = allocator.free_threads(cpu_in, workload_id, workloads)
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to free threads")
        return "Failed to free threads", 500


@app.route('/rebalance', methods=['PUT'])
def rebalance():
    allocator = get_cpu_allocator()

    if allocator is None:
        log.error("Cannot rebalance threads, CPU allocator is not set.")
        return "CPU allocator not set", 500

    try:
        body = request.get_json()
        cpu_in, workloads = get_rebalance_arguments(body)
        cpu_out = allocator.rebalance(cpu_in, workloads)
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to rebalance")
        return "Failed to rebalance", 500


