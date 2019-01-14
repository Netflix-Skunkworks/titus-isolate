from threading import RLock

import schedule

from titus_isolate import log
from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.constants import PROPERTIES

PROPERTY_CHANGE_DETECTION_INTERVAL_SEC = 10


class ConfigManager:

    def __init__(
            self,
            property_provider=AgentPropertyProvider(),
            property_change_interval=PROPERTY_CHANGE_DETECTION_INTERVAL_SEC):

        self.update_count = 0

        self.__property_provider = property_provider
        self.__config_map = {}
        self.__lock = RLock()

        self.__update_properties()
        schedule.every(property_change_interval).seconds.do(self.__update_properties)

    def __update_properties(self):
        for prop in PROPERTIES:
            self.update(prop, self.__property_provider.get(prop))

        self.update_count += 1

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

    def get(self, key, default=None):
        with self.__lock:
            value = self.__property_provider.get(key)
            self.update(key, value)

            return self.__config_map.get(key, default)
