from titus_isolate.metrics.linux_context_provider import TASK_ID_KEY, JOB_ID_KEY
from titus_isolate.metrics.titus_context_provider import TitusContextProvider
from titus_isolate.metrics.utils import get_env_from_file


class TestContextProvider(TitusContextProvider):
    def __init__(self, env_file_path):
        self.__env_map = get_env_from_file(env_file_path)

    def get_task_id(self, pid):
        return self.__env_map.get(TASK_ID_KEY, None)

    def get_job_id(self, pid):
        return self.__env_map.get(JOB_ID_KEY, None)
