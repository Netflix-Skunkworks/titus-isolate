import datetime
import os
import socket
import uuid

import requests

from titus_isolate import log
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.utils import get_workload_monitor_manager, get_config_manager


def send_event_msg(msg, address):
    log.debug("Sending to keystone address: '{}' msg: '{}'".format(address, msg))
    r = requests.post(address, json=msg)
    log.debug("Received response: '{}'".format(r))
    return r


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


def __get_cpu_event(cpu: Cpu, usage: dict, workloads: dict):
    return {
        "uuid": str(uuid.uuid4()),
        "payload": {
            "instance": get_config_manager().get_str('EC2_INSTANCE_ID'),
            "cpu": cpu.to_dict(),
            "cpu_usage": usage,
            "workloads": workloads
        }
    }


def get_cpu_event(cpu: Cpu, workloads: list) -> dict:
    workload_monitor_manager = get_workload_monitor_manager()
    if workload_monitor_manager is None:
        raise EventException("Failed to retrieve workload monitor manager to report cpu.")

    usage = workload_monitor_manager.get_cpu_usage(3600, 60)

    serializable_usage = {}
    for w_id, usage in usage.items():
        serializable_usage[w_id] = [str(u) for u in usage]

    serializable_workloads = {}
    for w in workloads:
        serializable_workloads[w.get_id()] = w.to_dict()

    return __get_cpu_event(cpu, serializable_usage, serializable_workloads)


class EventException(Exception):

    def __init__(self, msg):
        super().__init__(msg)


