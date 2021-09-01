import kubernetes

from titus_isolate.api.testing import is_testing
from titus_isolate.constants import DEFAULT_KUBECONFIG_PATH

core_api = None
if not is_testing():
    core_api = kubernetes.client.CoreV1Api(
        kubernetes.config.new_client_from_config(config_file=DEFAULT_KUBECONFIG_PATH))
