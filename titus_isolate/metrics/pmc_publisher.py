import time
from threading import Thread

import schedule as schedule

from titus_isolate.utils import get_logger

log = get_logger()


class PmcPublisher:

    def __init__(self, pmc_provider, publish_interval=10, sleep_interval=1):
        self.__provider = pmc_provider
        self.__publish_interval = publish_interval
        self.__sleep_interval = sleep_interval
        schedule.every(publish_interval).seconds.do(self.__publish_metrics)

        self.__worker_thread = Thread(target=self.__schedule_loop)
        self.__worker_thread.daemon = True
        self.__worker_thread.start()

    def __schedule_loop(self):
        while True:
            schedule.run_pending()
            time.sleep(self.__sleep_interval)

    def __publish_metrics(self):
        log.info("Getting metrics")
        metrics = self.__provider.get_metrics(self.__publish_interval)
        log.info("Publishing {} PMC metrics".format(len(metrics)))

        for metric in metrics:
            log.info(metric)
