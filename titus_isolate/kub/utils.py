from kubernetes.client import V1Node

from titus_isolate.config.constants import EC2_INSTANCE_ID
from titus_isolate.kub import core_api
from titus_isolate.utils import get_config_manager


def get_node() -> V1Node:
    return core_api.read_node(get_node_name())


def get_node_name() -> str:
    return get_config_manager().get_cached_str(EC2_INSTANCE_ID)
