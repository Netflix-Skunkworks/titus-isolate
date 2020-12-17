from functools import lru_cache

from titus_isolate.config.agent_property_provider import AgentPropertyProvider


class ConfigManager:

    def __init__(self, property_provider=AgentPropertyProvider()):
        self.__property_provider = property_provider

    def get_str(self, key, default=None) -> str:
        value = self.__property_provider.get(key)

        if value is None:
            return default
        else:
            return value

    def get_float(self, key, default=None) -> float:
        return float(self.get_str(key, default))

    def get_int(self, key, default=None) -> int:
        return int(self.get_str(key, default))

    def get_bool(self, key, default=None) -> bool:
        return bool(self.get_str(key, default))

    @lru_cache(maxsize=None)
    def get_cached_str(self, key, default=None) -> str:
        return self.get_str(key, default)

    @lru_cache(maxsize=None)
    def get_cached_float(self, key, default=None) -> float:
        return self.get_float(key, default)

    @lru_cache(maxsize=None)
    def get_cached_int(self, key, default=None) -> int:
        return self.get_int(key, default)

    @lru_cache(maxsize=None)
    def get_cached_bool(self, key, default=None) -> bool:
        return self.get_bool(key, default)

    def get_region(self) -> str:
        return self.get_cached_str('EC2_REGION')

    def get_environment(self) -> str:
        return self.get_cached_str('NETFLIX_ENVIRONMENT')

    def get_stack(self) -> str:
        return self.get_cached_str('NETFLIX_STACK')

    def get_instance(self) -> str:
        return self.get_cached_str('EC2_INSTANCE_ID')
