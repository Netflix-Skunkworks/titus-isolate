from titus_isolate.cgroup.utils import wait_for_files
from titus_isolate.config.constants import WAIT_CGROUP_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC, WAIT_JSON_FILE_KEY, \
    DEFAULT_WAIT_JSON_FILE_SEC
from titus_isolate.utils import get_config_manager


class FileManager:

    @staticmethod
    def wait_for_files(container_name):
        cgroup_file_wait_timeout = int(get_config_manager().get(WAIT_CGROUP_FILE_KEY, DEFAULT_WAIT_CGROUP_FILE_SEC))
        json_file_wait_timeout = int(get_config_manager().get(WAIT_JSON_FILE_KEY, DEFAULT_WAIT_JSON_FILE_SEC))

        wait_for_files(container_name, cgroup_file_wait_timeout, json_file_wait_timeout)
