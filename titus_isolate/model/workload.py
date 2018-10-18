class Workload:
    def __init__(self, identifier, thread_count):
        self.__identifier = identifier
        self.__thread_count = int(thread_count)

        if self.__thread_count < 0:
            raise ValueError("A workload must request at least 0 threads.")

    def get_id(self):
        return self.__identifier

    def get_thread_count(self):
        return self.__thread_count
