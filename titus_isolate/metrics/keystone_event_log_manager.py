import datetime
import uuid
from queue import Queue
from threading import Thread
from typing import Optional

from titus_isolate import log
from titus_isolate.config.constants import EVENT_LOG_FORMAT_STR
from titus_isolate.metrics.constants import EVENT_LOG_SUCCESS, EVENT_LOG_RETRY, EVENT_LOG_FAILURE
from titus_isolate.metrics.event_log import send_event_msg, get_event_msg
from titus_isolate.metrics.event_log_manager import EventLogManager
from titus_isolate.utils import get_config_manager


class KeystoneEventLogManager(EventLogManager):

    def __init__(self):
        self.__address = self.__get_address()
        log.info("Set keystone address to: {}".format(self.__address))

        self.__enabled = self.__address is not None

        self.__q = Queue()

        self.__reg = None
        self.__succeeded_msg_count = 0
        self.__retry_msg_count = 0
        self.__failed_msg_count = 0

        self.__processing_thread = Thread(target=self.__process_events)
        self.__processing_thread.start()

    def report_event(self, payload: dict):
        try:
            payload['ts'] = str(datetime.datetime.utcnow())
            event = {
                "uuid": str(uuid.uuid4()),
                "payload": payload
            }
            msg = get_event_msg(event)
            self.__q.put_nowait(msg)
        except Exception:
            self.__failed_msg_count += 1
            log.exception("Failed to report event for payload: {}".format(payload))

    def set_registry(self, registry, tags):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(EVENT_LOG_SUCCESS, tags).set(self.__succeeded_msg_count)
        self.__reg.gauge(EVENT_LOG_RETRY, tags).set(self.__retry_msg_count)
        self.__reg.gauge(EVENT_LOG_FAILURE, tags).set(self.__failed_msg_count)

    def __process_events(self):
        while True:
            try:
                msg = self.__q.get()
                if not self.__enabled:
                    log.warning("Dropping keystone event because keystone is disabled")
                    continue

                log.debug("Sending event log message: {}".format(msg))
                response = send_event_msg(msg, self.__address)

                if response.status_code != 200:
                    log.error("Re-enqueuing failed event log message: {}".format(response.content))
                    self.__retry_msg_count += 1
                    self.__q.put_nowait(msg)
                else:
                    self.__succeeded_msg_count += 1
            except Exception:
                self.__failed_msg_count += 1
                log.exception("Failed to process event log message.")

    def __get_address(self) -> Optional[str]:
        config_manager = get_config_manager()
        region = config_manager.get_region()
        env = config_manager.get_environment()
        format_str = config_manager.get_str(EVENT_LOG_FORMAT_STR)
        if format_str is None:
            log.warning("Keystone is not enabled in this region env: %s %s", region, env)
            return None

        stream = 'titus_isolate'
        return format_str.format(region, env, stream)
