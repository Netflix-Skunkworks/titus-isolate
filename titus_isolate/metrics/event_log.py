import socket

import requests

from titus_isolate import log
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.utils import get_event_log_manager


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


def get_cpu_event(request: AllocateRequest, response: AllocateResponse):
    return {
        "request": request.to_dict(),
        "response": response.to_dict(),
    }


def report_cpu_event(request: AllocateRequest, response: AllocateResponse):
    event_log_manager = get_event_log_manager()
    if event_log_manager is None:
        log.warning("Event log manager is not set.")
        return

    event_log_manager.report_event(get_cpu_event(request, response))


class EventException(Exception):

    def __init__(self, msg):
        super().__init__(msg)
