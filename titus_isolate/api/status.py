import json
import time

from flask import Flask

from titus_isolate.config.constants import TITUS_ISOLATE_BLOCK_SEC, DEFAULT_TITUS_ISOLATE_BLOCK_SEC
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.utils import get_config_manager

app = Flask(__name__)
__workload_manager = None
__event_manager = None
__workload_monitor_manager = None


def set_wm(workload_manager):
    global __workload_manager
    __workload_manager = workload_manager


def set_em(event_manager):
    global __event_manager
    __event_manager = event_manager


def set_workload_monitor_manager(workload_monitor_manager):
    global __workload_monitor_manager
    __workload_monitor_manager = workload_monitor_manager


@app.route('/isolate/<workload_id>')
def isolate_workload(workload_id, timeout=None):
    if timeout is None:
        timeout = int(get_config_manager().get(TITUS_ISOLATE_BLOCK_SEC, DEFAULT_TITUS_ISOLATE_BLOCK_SEC))

    deadline = time.time() + timeout
    while time.time() < deadline:
        if __workload_manager.is_isolated(workload_id):
            return json.dumps({'workload_id': workload_id}), 200, {'ContentType': 'application/json'}
        time.sleep(0.1)

    return json.dumps({'unknown_workload_id': workload_id}), 404, {'ContentType': 'application/json'}


@app.route('/workloads')
def get_workloads():
    workloads = [w.to_dict() for w in __workload_manager.get_workloads()]
    return json.dumps(workloads)


@app.route('/isolated_workload_ids')
def get_isolated_workload_ids():
    return json.dumps(__workload_manager.get_isolated_workload_ids())


@app.route('/cpu')
def get_cpu():
    packages = []
    for p in __workload_manager.get_cpu().get_packages():

        cores = []
        for c in p.get_cores():

            threads = []
            for t in c.get_threads():
                threads.append({
                    "id": t.get_id(),
                    "workload_id": t.get_workload_id()
                })
            cores.append({
                "id": c.get_id(),
                "threads": threads
            })

        packages.append({
            "id": p.get_id(),
            "cores": cores
        })

    response = {
        "packages": packages
    }

    return json.dumps(response)


@app.route('/violations')
def get_violations():
    return json.dumps({
        "cross_package": get_cross_package_violations(__workload_manager.get_cpu()),
        "shared_core": get_shared_core_violations(__workload_manager.get_cpu())
    })


@app.route('/status')
def get_wm_status():
    return json.dumps({
        "event_manager": {
            "queue_depth": __event_manager.get_queue_depth(),
            "success_count": __event_manager.get_success_count(),
            "error_count": __event_manager.get_error_count(),
            "processed_count": __event_manager.get_processed_count()
        },
        "workload_manager": {
            "cpu_allocator": __workload_manager.get_allocator_name(),
            "workload_count": len(__workload_manager.get_workloads()),
            "isolated_workload_count": len(__workload_manager.get_isolated_workload_ids()),
            "success_count": __workload_manager.get_success_count(),
            "error_count": __workload_manager.get_error_count(),
            "added_count": __workload_manager.get_added_count(),
            "removed_count": __workload_manager.get_removed_count()
        }
    })


@app.route('/metrics/raw')
def get_metrics():
    return json.dumps(__workload_monitor_manager.to_dict())


@app.route('/metrics/cpu_usage/<workload_id>/<seconds>')
def get_cpu_usage(workload_id, seconds):
    cpu_usage = __workload_monitor_manager.get_cpu_usage(seconds)

    if workload_id.lower() == 'all':
        return json.dumps(cpu_usage)

    if workload_id in cpu_usage:
        return json.dumps(cpu_usage[workload_id])

    return json.dumps({'unknown_workload_id': workload_id}), 404, {'ContentType': 'application/json'}
