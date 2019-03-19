import datetime
import os
import socket
import uuid

import requests

from titus_isolate import log
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.config.constants import EVENT_LOG_FORMAT_STR
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.utils import get_config_manager


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


def get_cpu_state_event(cpu: Cpu):
    return {
        "uuid": str(uuid.uuid4()),
        "payload": {
            "ts": str(datetime.datetime.utcnow()),
            "instance": os.environ['EC2_INSTANCE_ID'],
            "cpu": cpu.to_dict()
        }
    }


def get_cpu_usage_event(usage: dict):
    return {
        "uuid": str(uuid.uuid4()),
        "payload": {
            "ts": str(datetime.datetime.utcnow()),
            "instance": os.environ['EC2_INSTANCE_ID'],
            "cpu_usage": usage
        }
    }


def get_workload_type_event(workload_type_map: dict):
    return {
        "uuid": str(uuid.uuid4()),
        "payload": {
            "ts": str(datetime.datetime.utcnow()),
            "instance": os.environ['EC2_INSTANCE_ID'],
            "workload_types": workload_type_map
        }
    }


def report_cpu_state(cpu: Cpu):
    address = __get_address()
    if address is None:
        return

    msg = get_event_msg(get_cpu_state_event(cpu))
    log.debug("cpu_state: {}".format(msg))
    send_event_msg(msg, address)


def report_cpu_usage(usage: dict):
    address = __get_address()
    if address is None:
        return

    serializable_usage = {}
    for w_id, usage in usage.items():
        serializable_usage[w_id] = [str(u) for u in usage]

    msg = get_event_msg(get_cpu_usage_event(serializable_usage))
    log.debug("cpu_usage: {}".format(msg))
    send_event_msg(msg, address)


def report_workload_types(workloads: list):
    address = __get_address()
    if address is None:
        return

    w_type_map = {}
    for w in workloads:
        w_type_map[str(w.get_id())] = w.get_type()

    msg = get_event_msg(get_workload_type_event(w_type_map))
    log.debug("workload_types: {}".format(msg))
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
