import requests

from titus_isolate.config.property_provider import PropertyProvider
from titus_isolate.utils import get_logger

PROPERTY_URL_ROOT = 'http://localhost:3002/properties'

log = get_logger()


class AgentPropertyProvider(PropertyProvider):

    def get(self, key):
        url = self.__get_static_property_url(key)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            log.debug("Failed to retrieve property '{}' with response: '{}'".format(key, response))
            return None

        return response.text.upper()

    @staticmethod
    def __get_static_property_url(key):
        return '{}/property/{}'.format(PROPERTY_URL_ROOT, key)
