import os

from titus_isolate.config.property_provider import PropertyProvider


class EnvPropertyProvider(PropertyProvider):

    def get(self, key):
        return os.environ.get(key, None)
