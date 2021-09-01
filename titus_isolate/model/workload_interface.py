from abc import abstractmethod


class Workload:

    @abstractmethod
    def get_task_id(self) -> str:
        pass

    @abstractmethod
    def get_job_id(self) -> str:
        pass

    @abstractmethod
    def get_thread_count(self) -> int:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass
