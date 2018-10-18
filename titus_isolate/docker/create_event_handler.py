import json
import logging

from titus_isolate.docker.constants import ACTION, ACTOR, ATTRIBUTES, CPU_LABEL_KEY, CREATE, NAME
from titus_isolate.model.workload import Workload

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
log = logging.getLogger()


class CreateEventHandler:
    def __init__(self, resource_manager):
        self.__resource_manager = resource_manager
        self.__ignored_event_count = 0
        self.__handled_event_count = 0

    def handle(self, event):
        event = json.loads(event)
        if not self.relevant(event):
            return

        name = self.__get_container_name(event)
        cpus = self.__get_cpu_count(event)
        workload = Workload(name, cpus)

        log.info("Handling CREATE event, assigning threads to workload: '{}'".format(workload.get_id()))
        self.__resource_manager.assign_threads(workload)
        self.__handled_event_count += 1

    def get_ignored_event_count(self):
        return self.__ignored_event_count

    def get_handled_event_count(self):
        return self.__handled_event_count

    def relevant(self, event):
        if not event[ACTION] == CREATE:
            log.debug("Ignoring irrelevant event: '{}'".format(event))
            self.__ignored_event_count += 1
            return False

        if CPU_LABEL_KEY not in event[ACTOR][ATTRIBUTES]:
            log.warning("Ignoring container created without label: '{}'".format(CPU_LABEL_KEY))
            self.__ignored_event_count += 1
            return False

        return True

    @staticmethod
    def __get_cpu_count(create_event):
        return int(create_event[ACTOR][ATTRIBUTES][CPU_LABEL_KEY])

    @staticmethod
    def __get_container_name(create_event):
        return create_event[ACTOR][ATTRIBUTES][NAME]
