from threading import RLock

import schedule

from titus_isolate import log
from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.constants import PROPERTIES, ALLOCATOR_KEY
from titus_isolate.constants import ALLOCATOR_CONFIG_CHANGE_EXIT
from titus_isolate.real_exit_handler import RealExitHandler

PROPERTY_CHANGE_DETECTION_INTERVAL_SEC = 10


class ConfigManager:

    def __init__(
            self,
            property_provider=AgentPropertyProvider(),
            property_change_interval=PROPERTY_CHANGE_DETECTION_INTERVAL_SEC,
            exit_handler=RealExitHandler()):

        self.update_count = 0

        self.__property_provider = property_provider
        self.__exit_handler = exit_handler
        self.__config_map = {}
        self.__lock = RLock()

        # __watchers needs to be non-None when calling __update_properties(), but we don't want
        # to update watchers on initialization
        self.__watchers = []
        self.__update_properties()
        self.__watchers = [self.__handle_allocator_update]

        schedule.every(property_change_interval).seconds.do(self.__update_properties)

    def __update_properties(self):
        for prop in PROPERTIES:
            self.update(prop, self.__property_provider.get(prop))

        self.update_count += 1

    def __handle_allocator_update(self, key, old_value, new_value):
        if key != ALLOCATOR_KEY:
            return

        log.info("CPU allocator property: '{}' changed from '{}' to '{}' exiting...".format(key, old_value, new_value))
        self.__exit_handler.exit(ALLOCATOR_CONFIG_CHANGE_EXIT)

    def __update_watchers(self, key, old_value, new_value):
        for watcher in self.__watchers:
            watcher(key, old_value, new_value)

    def update(self, key, value):
        with self.__lock:
            old_value = self.__config_map.get(key, None)

            if value is None:
                self.__config_map.pop(key, None)
            else:
                self.__config_map[key] = value

            updated = old_value != value
            if updated:
                log.info("Updated '{}' from: '{}' to: '{}'".format(key, old_value, value))
                self.__update_watchers(key, old_value, value)

            return updated

    def get(self, key, default=None):
        with self.__lock:
            value = self.__property_provider.get(key)
            self.update(key, value)

            return self.__config_map.get(key, default)
