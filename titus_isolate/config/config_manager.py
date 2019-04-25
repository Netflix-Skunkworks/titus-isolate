from titus_isolate.config.agent_property_provider import AgentPropertyProvider


class ConfigManager:

    def __init__(self, property_provider=AgentPropertyProvider()):
        self.__property_provider = property_provider

    def get_str(self, key, default=None):
        value = self.__property_provider.get(key)

        if value is None:
            return default
        else:
            return value

    def get_float(self, key, default=None):
        return float(self.get_str(key, default))

    def get_int(self, key, default=None):
        return int(self.get_str(key, default))

    def get_bool(self, key, default= None):
        return bool(self.get_str(key, default))

    def get_region(self):
        return self.__property_provider.get('EC2_REGION')

    def get_environment(self):
        return self.__property_provider.get('NETFLIX_ENVIRONMENT')

    def get_stack(self):
        return self.__property_provider.get('NETFLIX_STACK')
