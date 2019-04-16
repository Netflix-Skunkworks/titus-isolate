import logging
import os
import sys
from threading import Lock

from flask import Flask, request, jsonify

from titus_isolate import log
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.utils import parse_workload, parse_cpu, parse_cpu_usage
from titus_isolate.api.testing import is_testing
from titus_isolate.config.constants import CPU_ALLOCATOR
from titus_isolate.config.env_property_provider import EnvPropertyProvider
from titus_isolate.isolate.utils import get_allocator
from titus_isolate.metrics.constants import SOLVER_GET_CPU_ALLOCATOR_SUCCESS, SOLVER_GET_CPU_ALLOCATOR_FAILURE, \
    SOLVER_ASSIGN_THREADS_SUCCESS, SOLVER_ASSIGN_THREADS_FAILURE, SOLVER_FREE_THREADS_SUCCESS, \
    SOLVER_FREE_THREADS_FAILURE, SOLVER_REBALANCE_SUCCESS, SOLVER_REBALANCE_FAILURE
from titus_isolate.metrics.keystone_event_log_manager import KeystoneEventLogManager
from titus_isolate.metrics.metrics_manager import MetricsManager
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.predict.cpu_usage_predictor_manager import CpuUsagePredictorManager
from titus_isolate.utils import get_config_manager, set_cpu_usage_predictor_manager, set_config_manager, \
    start_periodic_scheduling

lock = Lock()
cpu_allocator = None

app = Flask(__name__)

log = logging.getLogger()
log.setLevel(logging.INFO)
logging.getLogger('schedule').setLevel(logging.WARN)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
LOG_FMT_STRING = '%(asctime)s,%(msecs)d %(levelname)s %(process)d [%(filename)s:%(lineno)d] %(message)s'
formatter = logging.Formatter(LOG_FMT_STRING)
handler.setFormatter(formatter)
log.addHandler(handler)


def get_cpu_allocator() -> CpuAllocator:
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


def __get_cpu_usage(body):
    return parse_cpu_usage(body["cpu_usage"])


def __get_instance_id(body):
    return body.get("instance_id", "unknown_instance_id")


def get_threads_arguments(body):
    workload_id = __get_workload_id(body)
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    cpu_usage = __get_cpu_usage(body)
    instance_id = __get_instance_id(body)
    return cpu, workload_id, workloads, cpu_usage, instance_id


def get_rebalance_arguments(body):
    cpu = __get_cpu(body)
    workloads = __get_workloads(body)
    cpu_usage = __get_cpu_usage(body)
    instance_id = __get_instance_id(body)
    return cpu, workloads, cpu_usage, instance_id


get_cpu_allocator_success_count = 0
get_cpu_allocator_failure_count = 0

assign_threads_success_count = 0
assign_threads_failure_count = 0

free_threads_success_count = 0
free_threads_failure_count = 0

rebalance_success_count = 0
rebalance_failure_count = 0


@app.route('/', methods=['GET'])
def health_check():
    return remote_get_cpu_allocator()


@app.route('/cpu_allocator', methods=['GET'])
def remote_get_cpu_allocator():
    allocator = get_cpu_allocator()
    if cpu_allocator is None:
        global get_cpu_allocator_failure_count
        get_cpu_allocator_failure_count += 1
        return "CPU allocator not set", 404

    global get_cpu_allocator_success_count
    get_cpu_allocator_success_count += 1
    return allocator.get_name()


@app.route('/assign_threads', methods=['PUT'])
def assign_threads():
    allocator = get_cpu_allocator()

    try:
        body = request.get_json()
        cpu_in, workload_id, workloads, cpu_usage, instance_id = get_threads_arguments(body)
        log.info("Assigning threads for workload: '{}' from: '{}'".format(workload_id, instance_id))
        cpu_out = allocator.assign_threads(cpu_in, workload_id, workloads, cpu_usage, instance_id)
        global assign_threads_success_count
        assign_threads_success_count += 1
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to assign threads")
        global assign_threads_failure_count
        assign_threads_failure_count += 1
        return "Failed to assign threads", 500


@app.route('/free_threads', methods=['PUT'])
def free_threads():
    allocator = get_cpu_allocator()

    try:
        body = request.get_json()
        cpu_in, workload_id, workloads, cpu_usage, instance_id = get_threads_arguments(body)
        log.info("Freeing threads for workload: '{}' from: '{}'".format(workload_id, instance_id))
        cpu_out = allocator.free_threads(cpu_in, workload_id, workloads, cpu_usage, instance_id)
        global free_threads_success_count
        free_threads_success_count += 1
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to free threads")
        global free_threads_failure_count
        free_threads_failure_count += 1
        return "Failed to free threads", 500


@app.route('/rebalance', methods=['PUT'])
def rebalance():
    allocator = get_cpu_allocator()

    try:
        body = request.get_json()
        cpu_in, workloads, cpu_usage, instance_id = get_rebalance_arguments(body)
        log.info("Rebalancing workloads: {}, from: '{}'".format(workloads.keys(), instance_id))
        cpu_out = allocator.rebalance(cpu_in, workloads, cpu_usage, instance_id)
        global rebalance_success_count
        rebalance_success_count += 1
        return jsonify(cpu_out.to_dict())
    except:
        log.exception("Failed to rebalance")
        global rebalance_failure_count
        rebalance_failure_count += 1
        return "Failed to rebalance", 500


class SolverMetricsReporter(MetricsReporter):
    def __init__(self):
        self.__reg = None

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        global get_cpu_allocator_success_count
        global get_cpu_allocator_failure_count
        global assign_threads_success_count
        global assign_threads_failure_count
        global free_threads_success_count
        global free_threads_failure_count
        global rebalance_success_count
        global rebalance_failure_count

        ec2_instance_id = 'EC2_INSTANCE_ID'

        tags = {}
        if ec2_instance_id in os.environ:
            tags["nf.node"] = os.environ[ec2_instance_id]

        tags["pid"] = str(os.getpid())

        self.__reg.gauge(SOLVER_GET_CPU_ALLOCATOR_SUCCESS, tags).set(get_cpu_allocator_success_count)
        self.__reg.gauge(SOLVER_GET_CPU_ALLOCATOR_FAILURE, tags).set(get_cpu_allocator_failure_count)
        self.__reg.gauge(SOLVER_ASSIGN_THREADS_SUCCESS, tags).set(assign_threads_success_count)
        self.__reg.gauge(SOLVER_ASSIGN_THREADS_FAILURE, tags).set(assign_threads_failure_count)
        self.__reg.gauge(SOLVER_FREE_THREADS_SUCCESS, tags).set(free_threads_success_count)
        self.__reg.gauge(SOLVER_FREE_THREADS_FAILURE, tags).set(free_threads_failure_count)
        self.__reg.gauge(SOLVER_REBALANCE_SUCCESS, tags).set(rebalance_success_count)
        self.__reg.gauge(SOLVER_REBALANCE_FAILURE, tags).set(rebalance_failure_count)


if __name__ != '__main__' and not is_testing():
    log.info("Configuring logging...")
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    log.info("Setting config manager...")
    config_manager = get_config_manager(EnvPropertyProvider())
    set_config_manager(config_manager)

    log.info("Setting up the cpu usage predictor manager...")
    cpu_predictor_manager = CpuUsagePredictorManager()
    set_cpu_usage_predictor_manager(cpu_predictor_manager)

    log.info("Setting cpu_allocator config manager...")
    alloc_str = config_manager.get_str(CPU_ALLOCATOR)
    cpu_allocator = get_allocator(alloc_str, config_manager)
    cpu_allocator.set_event_log_manager(KeystoneEventLogManager())
    set_cpu_allocator(cpu_allocator)

    log.info("Starting metrics reporting...")
    MetricsManager([SolverMetricsReporter(), cpu_allocator])
    start_periodic_scheduling()
