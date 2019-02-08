import schedule

from titus_isolate import log
from titus_isolate.config.config_manager import PROPERTY_CHANGE_DETECTION_INTERVAL_SEC
from titus_isolate.constants import ALLOCATOR_CONFIG_CHANGE_EXIT
from titus_isolate.isolate.utils import get_allocator


class CpuAllocatorWatcher:

    def __init__(
            self,
            config_manager,
            exit_handler,
            detection_interval=PROPERTY_CHANGE_DETECTION_INTERVAL_SEC):

        self.__config_manager = config_manager
        self.__exit_handler = exit_handler

        self.__last_allocator_name = get_allocator(self.__config_manager).__class__.__name__
        schedule.every(detection_interval).seconds.do(self.detect_allocator_change)

    def get_last_allocator_name(self):
        return self.__last_allocator_name

    def detect_allocator_change(self):
        current_allocator_name = get_allocator(self.__config_manager).__class__.__name__

        if current_allocator_name != self.__last_allocator_name:
            log.info("The CPU allocator has changed from: '{}' to: '{}'".format(
                self.__last_allocator_name, current_allocator_name))

            self.__exit_handler.exit(ALLOCATOR_CONFIG_CHANGE_EXIT)

