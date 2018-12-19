import abc


class TitusContextProvider(abc.ABC):

    @abc.abstractmethod
    def get_task_id(self, pid):
        pass

    @abc.abstractmethod
    def get_job_id(self, pid):
        pass
