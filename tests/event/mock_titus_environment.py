import titus_isolate.model.utils

class MockTitusEnvironment():
    def __init__(self):
        self.__workloads = {}


    def add_workload(self, workload):
        self.__workloads[workload.get_id()] = workload


    def mocked_get_workload_from_disk(self, identifier):
        if identifier in self.__workloads:
            return self.__workloads[identifier]
        return None

MOCK_TITUS_ENVIRONMENT = MockTitusEnvironment()
titus_isolate.model.utils.get_workload_from_disk = MOCK_TITUS_ENVIRONMENT.mocked_get_workload_from_disk
