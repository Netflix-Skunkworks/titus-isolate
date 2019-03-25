import json
import time

from flask import Flask

from titus_isolate.config.constants import TITUS_ISOLATE_BLOCK_SEC, DEFAULT_TITUS_ISOLATE_BLOCK_SEC
from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations
from titus_isolate.utils import get_config_manager, get_workload_manager, get_event_manager, \
    get_workload_monitor_manager

app = Flask(__name__)


@app.route('/isolate/<workload_id>')
def isolate_workload(workload_id, timeout=None):
    if timeout is None:
        timeout = int(get_config_manager().get(TITUS_ISOLATE_BLOCK_SEC, DEFAULT_TITUS_ISOLATE_BLOCK_SEC))

    deadline = time.time() + timeout
    while time.time() < deadline:
        if get_workload_manager().is_isolated(workload_id):
            return json.dumps({'workload_id': workload_id}), 200, {'ContentType': 'application/json'}
        time.sleep(0.1)

    return json.dumps({'unknown_workload_id': workload_id}), 404, {'ContentType': 'application/json'}


@app.route('/workloads')
def get_workloads():
    workloads = [w.to_dict() for w in get_workload_manager().get_workloads()]
    return json.dumps(workloads)


@app.route('/isolated_workload_ids')
def get_isolated_workload_ids():
    return json.dumps(get_workload_manager().get_isolated_workload_ids())


@app.route('/cpu')
def get_cpu():
    return json.dumps(get_workload_manager().get_cpu().to_dict())


@app.route('/violations')
def get_violations():
    return json.dumps({
        "cross_package": get_cross_package_violations(get_workload_manager().get_cpu()),
        "shared_core": get_shared_core_violations(get_workload_manager().get_cpu())
    })


@app.route('/status')
def get_wm_status():
    return json.dumps({
        "event_manager": {
            "queue_depth": get_event_manager().get_queue_depth(),
            "success_count": get_event_manager().get_success_count(),
            "error_count": get_event_manager().get_error_count(),
            "processed_count": get_event_manager().get_processed_count()
        },
        "workload_manager": {
            "cpu_allocator": get_workload_manager().get_allocator_name(),
            "workload_count": len(get_workload_manager().get_workloads()),
            "isolated_workload_count": len(get_workload_manager().get_isolated_workload_ids()),
            "success_count": get_workload_manager().get_success_count(),
            "error_count": get_workload_manager().get_error_count(),
            "added_count": get_workload_manager().get_added_count(),
            "removed_count": get_workload_manager().get_removed_count()
        }
    })


@app.route('/metrics/raw')
def get_metrics():
    return json.dumps(get_workload_monitor_manager().to_dict())


@app.route('/metrics/cpu_usage/<workload_id>/<seconds>/<granularity>')
def get_cpu_usage(workload_id, seconds, granularity):
    cpu_usage = get_workload_monitor_manager().get_cpu_usage(seconds, granularity)

    if workload_id.lower() == 'all':
        return json.dumps(cpu_usage)

    if workload_id in cpu_usage:
        return json.dumps(cpu_usage[workload_id])

    return json.dumps({'unknown_workload_id': workload_id}), 404, {'ContentType': 'application/json'}
