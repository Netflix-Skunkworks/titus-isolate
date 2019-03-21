import datetime
import os
import socket
import uuid

import requests

from titus_isolate import log
from titus_isolate.config.constants import EVENT_LOG_FORMAT_STR
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.utils import get_config_manager, get_workload_monitor_manager


def get_address(region, env, stream):
    format_str = get_config_manager().get(EVENT_LOG_FORMAT_STR, None)
    if format_str is None:
        return None

    return format_str.format(region, env, stream)


def send_event_msg(msg, address):
    log.debug("Sending to keystone address: '{}' msg: '{}'".format(address, msg))
    r = requests.post(address, json=msg)
    log.debug("Received response: '{}'".format(r))


def get_event_msg(event):
    app_name = "titus-isolate"
    host_name = socket.gethostname()
    ack = True

    return {
        "appName": app_name,
        "hostname": host_name,
        "ack": ack,
        "event": [event]
    }


def get_cpu_event(cpu: Cpu, usage: dict, workloads: dict):
    return {
        "uuid": str(uuid.uuid4()),
        "payload": {
            "ts": str(datetime.datetime.utcnow()),
            "instance": os.environ['EC2_INSTANCE_ID'],
            "cpu": cpu.to_dict(),
            "cpu_usage": usage,
            "workloads:": workloads
        }
    }


def report_cpu(cpu: Cpu, workloads):
    address = __get_address()
    if address is None:
        return

    workload_monitor_manager = get_workload_monitor_manager()
    if workload_monitor_manager is None:
        log.debug("Failed to retrieve workload monitor manager to report cpu.")
        return

    usage = workload_monitor_manager.get_cpu_usage(600, 60)

    serializable_usage = {}
    for w_id, usage in usage.items():
        serializable_usage[w_id] = [str(u) for u in usage]

    serializable_workloads = {}
    for w in workloads:
        serializable_workloads[w.get_id()] = w.to_dict()

    msg = get_event_msg(get_cpu_event(cpu, serializable_usage, serializable_workloads))
    log.debug("reporting cpu: {}".format(msg))
    send_event_msg(msg, address)


def __get_address():
    config_manager = get_config_manager()
    region = config_manager.get_region()
    env = config_manager.get_environment()
    stream = 'titus_isolate'

    address = get_address(region, env, stream)
    if address is None:
        log.error("Failed to retrieve event log address for region: '{}', env: '{}', stream: '{}'".format(
            region, env, stream))
        return None

    return address
