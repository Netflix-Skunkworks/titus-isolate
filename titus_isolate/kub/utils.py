from kubernetes.client import V1Node

from titus_isolate.config.constants import EC2_INSTANCE_ID
from titus_isolate.kub import core_api
from titus_isolate.kub.constants import ANNOTATION_KEY_INSTANCE_TYPE, UNKNOWN_INSTANCE_TYPE
from titus_isolate.utils import get_config_manager


def get_node() -> V1Node:
    return core_api.read_node(get_node_name())


def get_node_name() -> str:
    return get_config_manager().get_cached_str(EC2_INSTANCE_ID)


def get_instance_type(node : V1Node) -> str:
    if node.metadata is None:
        return UNKNOWN_INSTANCE_TYPE
    return node.metadata.annotations.get(ANNOTATION_KEY_INSTANCE_TYPE, UNKNOWN_INSTANCE_TYPE)
