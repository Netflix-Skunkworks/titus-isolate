
from titus_isolate.event.constants import *
from titus_isolate.model.constants import *
from titus_isolate.model.workload_interface import Workload


class LegacyWorkload(Workload):

    def __init__(self, task_id, job_id, thread_count):
        self.__task_id = task_id
        self.__job_id = job_id
        self.__thread_count = int(thread_count)

        if self.__thread_count < 0:
            raise ValueError("A workload must request at least 0 threads.")

    def get_task_id(self) -> str:
        return self.__task_id

    def get_job_id(self) -> str:
        return self.__job_id

    def get_thread_count(self) -> int:
        return self.__thread_count

    def to_dict(self):
        return {
            TASK_ID_KEY: str(self.get_task_id()),
            JOB_ID_KEY: self.get_job_id(),
            THREAD_COUNT_KEY: self.get_thread_count()
        }

    def __str__(self):
        return json.dumps(self.to_dict())
