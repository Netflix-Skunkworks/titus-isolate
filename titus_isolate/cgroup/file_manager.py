from abc import abstractmethod


class FileManager:

    @abstractmethod
    def wait_for_files(self, container_name, timeout):
        pass
