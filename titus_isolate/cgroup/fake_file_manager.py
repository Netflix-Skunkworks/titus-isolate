from titus_isolate.cgroup.file_manager import FileManager


class FakeFileManager(FileManager):

    def __init__(self, success=True):
        self.__success = success

    def wait_for_files(self, container_name, timeout):
        if self.__success:
            return
        else:
            raise TimeoutError("Fake file manager timing out for tests.")
