
class TitusPmc:
    def __init__(self, timestamp, duration, name, value, pid, cpu_id, job_id, task_id):
        self.__timestamp = timestamp
        self.__duration = duration
        self.__name = name
        self.__value = value
        self.__pid = pid
        self.__cpu_id = cpu_id
        self.__job_id = job_id
        self.__task_id = task_id

    def get_timestamp(self):
        return self.__timestamp

    def get_duration(self):
        return self.__duration

    def get_name(self):
        return self.__name

    def get_value(self):
        return self.__value

    def get_pid(self):
        return self.__pid

    def get_cpu_id(self):
        return self.__cpu_id

    def get_job_id(self):
        return self.__job_id

    def get_task_id(self):
        return self.__task_id

    def __str__(self):
        return "timestamp: {}, sample_duration: {}, name: {}, value: {}, pid: {}, cpu_id: {}, job_id: {}, task_id: {}" \
            .format(self.get_timestamp(),
                    self.get_duration(),
                    self.get_name(),
                    self.get_value(),
                    self.get_pid(),
                    self.get_cpu_id(),
                    self.get_job_id(),
                    self.get_task_id())
