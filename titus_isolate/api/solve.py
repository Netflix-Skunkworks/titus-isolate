import logging
import sys
from threading import Lock

from flask import Flask, request, jsonify

from titus_isolate import log
from titus_isolate.allocate.utils import parse_workload, parse_cpu, parse_cpu_usage
from titus_isolate.config.constants import CPU_ALLOCATOR, LOG_FMT_STRING
from titus_isolate.config.env_property_provider import EnvPropertyProvider
from titus_isolate.isolate.utils import get_allocator
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager
from titus_isolate.utils import get_config_manager, set_cpu_usage_predictor_manager, set_config_manager

lock = Lock()
cpu_allocator = None

app = Flask(__name__)

log = logging.getLogger()
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(LOG_FMT_STRING)
handler.setFormatter(formatter)
log.addHandler(handler)

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


def set_usage_predictor_manager():
    # Start the cpu usage predictor manager
    log.info("Setting up the cpu usage predictor manager...")
    cpu_predictor_manager = CpuUsagePredictorManager()
    set_cpu_usage_predictor_manager(cpu_predictor_manager)


def get_cpu_allocator():
    with lock:
        global cpu_allocator
        if cpu_allocator is None:
            config_manager = get_config_manager(EnvPropertyProvider())
            set_config_manager(config_manager)

            set_usage_predictor_manager()
            alloc_str = config_manager.get(CPU_ALLOCATOR)
            cpu_allocator = get_allocator(alloc_str, config_manager)

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


def __get_cpu_usage(body):
    return parse_cpu_usage(body["cpu_usage"])


def get_threads_arguments(body):
    workload_id = __get_workload_id(body)
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    cpu_usage = __get_cpu_usage(body)
    return cpu, workload_id, workloads, cpu_usage


def get_rebalance_arguments(body):
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    cpu_usage = __get_cpu_usage(body)
    return cpu, workloads, cpu_usage


@app.route('/cpu_allocator', methods=['GET'])
def remote_get_cpu_allocator():
    allocator = get_cpu_allocator()
    if cpu_allocator is None:
        return "CPU allocator not set", 404

    return allocator.__class__.__name__


@app.route('/assign_threads', methods=['PUT'])
def assign_threads():
    allocator = get_cpu_allocator()

    if allocator is None:
        log.error("Cannot assign threads, CPU allocator is not set.")
        return "CPU allocator not set", 500

    try:
        body = request.get_json()
        cpu_in, workload_id, workloads, cpu_usage = get_threads_arguments(body)
        cpu_out = allocator.assign_threads(cpu_in, workload_id, workloads, cpu_usage)
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
        cpu_in, workload_id, workloads, cpu_usage = get_threads_arguments(body)
        cpu_out = allocator.free_threads(cpu_in, workload_id, workloads, cpu_usage)
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
        cpu_in, workloads, cpu_usage = get_rebalance_arguments(body)
        cpu_out = allocator.rebalance(cpu_in, workloads, cpu_usage)
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to rebalance")
        return "Failed to rebalance", 500


