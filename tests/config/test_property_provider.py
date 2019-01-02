from titus_isolate.config.property_provider import PropertyProvider


class TestPropertyProvider(PropertyProvider):
    def __init__(self, prop_map):
        self.map = prop_map

    def get(self, key):
        return self.map.get(key, None)
