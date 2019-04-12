import schedule

from titus_isolate import log
from titus_isolate.constants import GENERIC_PROPERTY_CHANGE_EXIT, ALLOCATOR_CONFIG_CHANGE_EXIT
from titus_isolate.isolate.utils import get_fallback_allocator

PROPERTY_CHANGE_DETECTION_INTERVAL_SEC = 10


class RestartPropertyWatcher:

    def __init__(
            self,
            config_manager,
            exit_handler,
            properties,
            detection_interval=PROPERTY_CHANGE_DETECTION_INTERVAL_SEC):

        self.__config_manager = config_manager
        self.__exit_handler = exit_handler
        self.__properties = properties

        self.__original_properties = {}
        for p in properties:
            self.__original_properties[p] = config_manager.get_str(p)

        self.__original_primary_allocator_name =\
            get_fallback_allocator(config_manager).get_primary_allocator().__class__.__name__

        log.info("Starting watching for changes to properties: {}".format(properties))
        for k, v in self.__original_properties.items():
            log.info("{}: {}".format(k, v))

        schedule.every(detection_interval).seconds.do(self.detect_changes)

    def detect_changes(self):
        self.__detect_property_changes()
        self.__detect_ab_changes()

    def __detect_property_changes(self):
        for p in self.__properties:
            original_value = self.__original_properties[p]
            curr_value = self.__config_manager.get_str(p)
            log.debug("property: '{}' original: '{}' current: '{}'".format(p, original_value, curr_value))

            if original_value != curr_value:
                log.info("Restarting because property: '{}' changed from: '{}' to: '{}'".format(
                    p, original_value, curr_value))

                self.__exit_handler.exit(GENERIC_PROPERTY_CHANGE_EXIT)

    def __detect_ab_changes(self):
        curr_primary_allocator_name = get_fallback_allocator(self.__config_manager).get_primary_allocator().__class__.__name__
        if self.__original_primary_allocator_name != curr_primary_allocator_name:
            log.info("Restarting because primary CPU allocator changed from: '{}' to: '{}'".format(
                self.__original_primary_allocator_name, curr_primary_allocator_name))
            self.__exit_handler.exit(ALLOCATOR_CONFIG_CHANGE_EXIT)
