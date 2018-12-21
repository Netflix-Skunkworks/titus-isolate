from pathlib import Path

from titus_isolate.utils import get_logger

log = get_logger()


def get_env_from_file(path):
    log.debug("Reading environment of: '{}'".format(path))
    if Path(path).is_file():
        with open(path, "r") as env_file:
            return __get_env_map(env_file.readline())
    else:
        return {}


def __get_env_map(raw_env):
    raw_vars = raw_env.split('\x00')

    env_map = {}
    for var in raw_vars:
        if '=' in var:
            (key, value) = var.split('=', 1)
            log.debug("key: {}, value: {}".format(key, value))
            env_map[key] = value

    return env_map

