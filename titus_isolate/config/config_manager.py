from threading import Lock

from titus_isolate import log
from titus_isolate.config.agent_property_provider import AgentPropertyProvider
from titus_isolate.config.constants import PROPERTIES, ALLOCATOR_KEY, WAIT_CGROUP_FILE_KEY
from titus_isolate.config.property_change_handler import PropertyChangeHandler
from titus_isolate.constants import ALLOCATOR_CONFIG_CHANGE_EXIT
from titus_isolate.real_exit_handler import RealExitHandler

PROPERTY_CHANGE_DETECTION_INTERVAL_SEC = 10


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

        PropertyChangeHandler(ALLOCATOR_KEY, self.__handle_allocator_update, property_provider, property_change_interval)
        PropertyChangeHandler(WAIT_CGROUP_FILE_KEY, self.__handle_cgroup_file_wait_update, property_provider, property_change_interval)

    def __handle_allocator_update(self, value):
        updated = self.update(ALLOCATOR_KEY, value)
        if not updated:
            self.ignored_iteration_count += 1
            return

        self.__exit_handler.exit(ALLOCATOR_CONFIG_CHANGE_EXIT)

    def __handle_cgroup_file_wait_update(self, value):
        self.update(WAIT_CGROUP_FILE_KEY, value)

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

            return updated

    def get(self, key, default=None):
        with self.__lock:
            return self.__config_map.get(key, default)
