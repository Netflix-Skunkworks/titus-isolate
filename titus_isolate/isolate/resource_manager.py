from titus_isolate.isolate.cpu import assign_threads


class ResourceManager:

    def __init__(self, cpu, docker_client):
        self.__cpu = cpu
        self.__docker_client = docker_client

    def assign_threads(self, workload):
        threads = assign_threads(self.__cpu, workload)
        thread_ids = self.__get_thread_ids_str(threads)
        self.__docker_client.containers.update(cpuset_cpus=thread_ids)

    @staticmethod
    def __get_thread_ids_str(threads):
        thread_ids = [str(thread.get_id()) for thread in threads]
        return ",".join(thread_ids)
