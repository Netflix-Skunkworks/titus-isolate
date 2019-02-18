from titus_isolate.config.agent_property_provider import AgentPropertyProvider


class ConfigManager:

    def __init__(self, property_provider=AgentPropertyProvider()):
        self.__property_provider = property_provider

    def get(self, key, default=None):
        value = self.__property_provider.get(key)

        if value is None:
            return default
        else:
            return value
