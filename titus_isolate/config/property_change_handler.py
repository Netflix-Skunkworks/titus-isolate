import schedule

from titus_isolate import log


class PropertyChangeHandler:
    def __init__(
            self,
            key,
            func,
            property_provider,
            change_detection_interval):
        self.__key = key
        self.__func = func
        self.__property_provider = property_provider

        schedule.every(change_detection_interval).seconds.do(self.__update_property)

    def __update_property(self):
        value = self.__property_provider.get(self.__key)
        log.debug("Handling property change for: '{}', to: '{}''".format(self.__key, value))
        self.__func(value)
