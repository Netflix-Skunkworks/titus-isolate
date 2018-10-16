class Thread:
    def __init__(self, processor_id):
        self.__processor_id = processor_id

    def get_processor_id(self):
        return self.__processor_id
