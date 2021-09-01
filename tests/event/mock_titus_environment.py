import titus_isolate.model.utils

from titus_isolate import log


class MockTitusEnvironment:
    def __init__(self):
        self.__workloads = {}

    def add_workload(self, workload):
        self.__workloads[workload.get_id()] = workload

    def mocked_get_workload(self, identifier):
        if identifier in self.__workloads:
            return self.__workloads[identifier]
        return None


log.info("setting up mock titus environment")
MOCK_TITUS_ENVIRONMENT = MockTitusEnvironment()
titus_isolate.model.utils.get_workload = MOCK_TITUS_ENVIRONMENT.mocked_get_workload
