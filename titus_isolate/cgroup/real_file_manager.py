from titus_isolate.cgroup.file_manager import FileManager
from titus_isolate.cgroup.utils import wait_for_files


class RealFileManager(FileManager):

    def wait_for_files(self, container_name, timeout):
        wait_for_files(container_name, timeout)
