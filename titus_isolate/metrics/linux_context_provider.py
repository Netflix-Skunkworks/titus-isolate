from threading import Lock

from titus_isolate.metrics.titus_context_provider import TitusContextProvider
from titus_isolate.metrics.utils import get_env_from_file
from titus_isolate.utils import get_logger

TASK_ID_KEY = 'TITUS_TASK_ID'
JOB_ID_KEY = 'TITUS_JOB_ID'
LINUX_PROC_ENV_PATH_FMT = '/proc/{}/environ'

log = get_logger()


def _get_linux_proc_environ_path(pid):
    return LINUX_PROC_ENV_PATH_FMT.format(pid)


class LinuxContextProvider(TitusContextProvider):

    def __init__(self):
        self.__lock = Lock()

    def get_task_id(self, pid):
        return self.__get_value(TASK_ID_KEY, pid)

    def get_job_id(self, pid):
        return self.__get_value(JOB_ID_KEY, pid)

    def __get_value(self, key, pid):
        with self.__lock:
            env_map = get_env_from_file(_get_linux_proc_environ_path(pid))

            return env_map.get(key, None)

