from threading import Lock

from flask import Flask, request, jsonify

from titus_isolate import log
from titus_isolate.allocate.utils import parse_workload, parse_cpu
from titus_isolate.config.env_property_provider import EnvPropertyProvider
from titus_isolate.isolate.utils import get_allocator
from titus_isolate.utils import get_config_manager

lock = Lock()
cpu_allocator = None

app = Flask(__name__)


def get_cpu_allocator():
    with lock:
        global cpu_allocator
        if cpu_allocator is None:
            config_manager = get_config_manager(EnvPropertyProvider())
            cpu_allocator = get_allocator(config_manager)

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


def get_threads_arguments(body):
    workload_id = __get_workload_id(body)
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    return cpu, workload_id, workloads


def get_rebalance_arguments(body):
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    return cpu, workloads


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


