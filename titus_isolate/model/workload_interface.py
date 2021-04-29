from abc import abstractmethod
from typing import List

from titus_isolate.model.duration_prediction import DurationPrediction


class Workload:

    @abstractmethod
    def get_object_type(self) -> type:
        pass

    @abstractmethod
    def get_id(self) -> str:
        pass

    @abstractmethod
    def get_job_id(self) -> str:
        pass

    @abstractmethod
    def get_thread_count(self) -> int:
        pass

    @abstractmethod
    def get_mem(self) -> float:
        pass

    @abstractmethod
    def get_disk(self) -> float:
        pass

    @abstractmethod
    def get_network(self) -> float:
        pass

    @abstractmethod
    def get_app_name(self) -> str:
        pass

    @abstractmethod
    def get_owner_email(self) -> str:
        pass

    @abstractmethod
    def get_image(self) -> str:
        pass

    @abstractmethod
    def get_command(self) -> str:
        pass

    @abstractmethod
    def get_entrypoint(self) -> str:
        pass

    @abstractmethod
    def get_type(self) -> str:
        pass

    @abstractmethod
    def is_burst(self) -> bool:
        pass

    @abstractmethod
    def is_static(self) -> bool:
        pass

    @abstractmethod
    def get_job_type(self) -> str:
        pass

    @abstractmethod
    def is_batch(self) -> bool:
        pass

    @abstractmethod
    def is_service(self) -> bool:
        pass

    # TODO: Remove
    @abstractmethod
    def get_creation_time(self):
        pass

    # TODO: Remove
    @abstractmethod
    def set_creation_time(self, creation_time):
        pass

    @abstractmethod
    def get_launch_time(self) -> int:
        """
        Launch time of workload in UTC unix seconds
        """
        pass

    @abstractmethod
    def is_opportunistic(self) -> bool:
        pass

    @abstractmethod
    def get_opportunistic_thread_count(self) -> int:
        pass

    @abstractmethod
    def get_duration_predictions(self) -> List[DurationPrediction]:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass
