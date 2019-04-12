from queue import Queue
from threading import Thread

from titus_isolate import log
from titus_isolate.config.constants import EVENT_LOG_FORMAT_STR
from titus_isolate.metrics.constants import EVENT_LOG_SUCCESS, EVENT_LOG_RETRY, EVENT_LOG_FAILURE
from titus_isolate.metrics.event_log import get_cpu_msg, EventException, send_event_msg
from titus_isolate.metrics.metrics_reporter import MetricsReporter
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.utils import get_config_manager


class KeystoneEventLogManager(MetricsReporter):

    def __init__(self):
        self.__set_address()
        self.__q = Queue()

        self.__reg = None
        self.__succeeded_msg_count = 0
        self.__retry_msg_count = 0
        self.__failed_msg_count = 0

        self.__processing_thread = Thread(target=self.__process_events)
        self.__processing_thread.start()

    def report_cpu(self, cpu: Cpu, workloads: list):
        try:
            self.__q.put_nowait(get_cpu_msg(cpu, workloads))
        except EventException:
            self.__failed_msg_count += 1
            log.exception("Failed to report cpu change event for cpu: {} and workloads: {}".format(cpu, workloads))

    def set_registry(self, registry):
        self.__reg = registry

    def report_metrics(self, tags):
        self.__reg.gauge(EVENT_LOG_SUCCESS, tags).set(self.__succeeded_msg_count)
        self.__reg.gauge(EVENT_LOG_RETRY, tags).set(self.__retry_msg_count)
        self.__reg.gauge(EVENT_LOG_FAILURE, tags).set(self.__failed_msg_count)

    def __process_events(self):
        while True:
            try:
                msg = self.__q.get()
                response = send_event_msg(msg, self.__address)

                if response.status_code != 200:
                    log.error("Re-enqueuing failed event log message: {}".format(response.content))
                    self.__retry_msg_count += 1
                    self.__q.put_nowait(msg)
                else:
                    self.__succeeded_msg_count += 1
            except:
                self.__failed_msg_count += 1
                log.exception("Failed to process event log message.")

    def __set_address(self):
        config_manager = get_config_manager()
        region = config_manager.get_region()
        env = config_manager.get_environment()
        format_str = config_manager.get_str(EVENT_LOG_FORMAT_STR)
        stream = 'titus_isolate'

        self.__address = format_str.format(region, env, stream)
        log.info("Set keystone address to: {}".format(self.__address))
