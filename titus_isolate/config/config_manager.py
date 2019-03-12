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

    def get_region(self):
        return self.__property_provider.get('EC2_REGION')

    def get_environment(self):
        return self.__property_provider.get('NETFLIX_ENVIRONMENT')
