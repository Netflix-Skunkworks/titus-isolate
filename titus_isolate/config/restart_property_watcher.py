from typing import List

import schedule

from titus_isolate import log
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.constants import GENERIC_PROPERTY_CHANGE_EXIT
from titus_isolate.exit_handler import ExitHandler

PROPERTY_CHANGE_DETECTION_INTERVAL_SEC = 10


class RestartPropertyWatcher:

    def __init__(
            self,
            config_manager: ConfigManager,
            exit_handler: ExitHandler,
            properties: List[str],
            detection_interval: int = PROPERTY_CHANGE_DETECTION_INTERVAL_SEC):

        self.__config_manager = config_manager
        self.__exit_handler = exit_handler
        self.__properties = properties

        log.info("Starting watching for changes to properties: {}".format(properties))
        for p in properties:
            v = config_manager.get_cached_str(p)
            log.info("{}: {}".format(p, v))

        schedule.every(detection_interval).seconds.do(self.detect_changes)

    def detect_changes(self):
        self.__detect_property_changes()

    def __detect_property_changes(self):
        for p in self.__properties:
            original_value = self.__config_manager.get_cached_str(p)
            curr_value = self.__config_manager.get_str(p)
            log.debug("property: '{}' original: '{}' current: '{}'".format(p, original_value, curr_value))

            if original_value != curr_value:
                log.info("Restarting because property: '{}' changed from: '{}' to: '{}'".format(
                    p, original_value, curr_value))

                self.__exit_handler.exit(GENERIC_PROPERTY_CHANGE_EXIT)
