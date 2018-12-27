import schedule as schedule

from titus_isolate.utils import get_logger

log = get_logger()


class PmcPublisher:

    def __init__(self, pmc_provider, subscribers, publish_interval=10):
        self.__provider = pmc_provider
        self.__subscribers = subscribers
        self.__publish_interval = publish_interval

        schedule.every(publish_interval).seconds.do(self.__publish_metrics)

    def __publish_metrics(self):
        try:
            metrics = self.__provider.get_metrics(self.__publish_interval)
            log.info("Publishing {} PMC metrics to {} subscribers".format(len(metrics), len(self.__subscribers)))

            for metric in metrics:
                log.debug(metric)
                for subscriber in self.__subscribers:
                    subscriber.handle_nowait(metric)
        except:
            log.exception("Failed to publish PMC metrics.")
