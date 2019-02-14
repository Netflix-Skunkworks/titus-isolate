import datetime
import os
import socket
import uuid

import requests

from titus_isolate import log
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


def get_event_msg(cpu: Cpu):
    app_name = "titus-isolate"
    host_name = socket.gethostname()
    ack = True

    events = [get_event(cpu)]

    return {
        "appName": app_name,
        "hostname": host_name,
        "ack": ack,
        "event": events
    }


def get_event(cpu: Cpu):
    return {
        "uuid": str(uuid.uuid4()),
        "payload": {
            "ts": str(datetime.datetime.utcnow()),
            "instance": os.environ['EC2_INSTANCE_ID'],
            "cpu": cpu.to_dict()
        }
    }


def report_cpu(cpu: Cpu):
    region = os.environ['EC2_REGION']
    env = os.environ['NETFLIX_ENVIRONMENT']
    stream = 'titus_isolate'

    address = get_address(region, env, stream)
    if address is None:
        log.error("Failed to retrieve event log address for region: '{}', env: '{}', stream: '{}'".format(
            region, env, stream))
        return

    msg = get_event_msg(cpu)
    send_event_msg(msg, address)
