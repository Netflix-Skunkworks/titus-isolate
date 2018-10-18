import logging

from titus_isolate.isolate.cpu import assign_threads

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


class ResourceManager:

    def __init__(self, cpu, docker_client):
        self.__cpu = cpu
        self.__docker_client = docker_client

    def assign_threads(self, workload):
        threads = assign_threads(self.__cpu, workload)
        thread_ids = self.__get_thread_ids_str(threads)
        log.info("Updating container: '{}' with cpuset_cpus: '{}'".format(workload.get_id(), thread_ids))
        self.__docker_client.containers.get(workload.get_id()).update(cpuset_cpus=thread_ids)

    @staticmethod
    def __get_thread_ids_str(threads):
        thread_ids = [str(thread.get_id()) for thread in threads]
        return ",".join(thread_ids)
