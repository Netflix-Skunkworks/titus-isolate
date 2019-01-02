import os
from threading import Lock

from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.constants import PROPERTIES, ALLOCATOR_KEY
from titus_isolate.config.property_change_handler import PropertyChangeHandler
from titus_isolate.constants import ALLOCATOR_CONFIG_CHANGE_EXIT
from titus_isolate.real_exit_handler import RealExitHandler
from titus_isolate.utils import get_logger

PROPERTY_CHANGE_DETECTION_INTERVAL_SEC = 10

log = get_logger()


class ConfigManager:

    def __init__(
            self,
            property_provider=AgentPropertyProvider(),
            property_change_interval=PROPERTY_CHANGE_DETECTION_INTERVAL_SEC,
            exit_handler=RealExitHandler()):
        self.__exit_handler = exit_handler
        self.__config_map = {}
        self.__lock = Lock()
        self.ignored_iteration_count = 0

        for prop in PROPERTIES:
            self.update(prop, property_provider.get(prop))

        PropertyChangeHandler(
            ALLOCATOR_KEY,
            self.__handle_allocator_update,
            property_provider,
            property_change_interval)

    def __handle_allocator_update(self, value):
        old_value = self.get(ALLOCATOR_KEY)
        self.__config_map[ALLOCATOR_KEY] = value
        log.info("Handling allocator change from: '{} to: '{}'".format(old_value, value))

        if old_value == value:
            self.ignored_iteration_count += 1
            return

        self.__exit_handler.exit(ALLOCATOR_CONFIG_CHANGE_EXIT)

    def update(self, key, value):
        with self.__lock:
            old_value = self.__config_map.get(key, None)
            log.info("Updating '{}' from: '{}' to: '{}'".format(key, old_value, value))
            self.__config_map[key] = value

    def get(self, key):
        with self.__lock:
            return self.__config_map.get(key, None)

