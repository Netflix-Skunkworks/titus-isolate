from titus_isolate import log
from titus_isolate.utils import get_config_manager


def get_required_property(key):
    value = get_config_manager().get_str(key)
    if value is None:
        log.error("Failed to retrieve property: '{}'".format(key))
        return None

    return value
