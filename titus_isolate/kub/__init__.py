import kubernetes

from titus_isolate.api.testing import is_testing
from titus_isolate.constants import DEFAULT_KUBECONFIG_PATH
from titus_isolate.utils import is_kubernetes

core_api = None
if (not is_testing()) and is_kubernetes():
    core_api = kubernetes.client.CoreV1Api(
        kubernetes.config.new_client_from_config(config_file=DEFAULT_KUBECONFIG_PATH))
