import json

ACTION = "Action"
ACTOR = "Actor"
ATTRIBUTES = "Attributes"
ID = "ID"
LOWERCASE_ID = "id"
NAME = "name"
TIME = "time"
TYPE = "Type"

CONTAINER = "container"
CREATE = "create"
DIE = "die"
REBALANCE = "rebalance"
RECONCILE = "reconcile"

CPU_LABEL_KEY = "com.netflix.titus.cpu"
MEM_LABEL_KEY = "com.netflix.titus.mem"
DISK_LABEL_KEY = "com.netflix.titus.disk"
NETWORK_LABEL_KEY = "com.netflix.titus.network"
WORKLOAD_TYPE_LABEL_KEY = "com.netflix.titus.workload.type"
IMAGE_LABEL_KEY = "image"
REQUIRED_LABELS = [
    CPU_LABEL_KEY,
    MEM_LABEL_KEY,
    DISK_LABEL_KEY,
    NETWORK_LABEL_KEY,
    IMAGE_LABEL_KEY,
    WORKLOAD_TYPE_LABEL_KEY]

STATIC = "static"
BURST = "burst"
WORKLOAD_TYPES = [STATIC, BURST]

REBALANCE_EVENT = json.dumps({ACTION: REBALANCE}).encode("utf-8")
RECONCILE_EVENT = json.dumps({ACTION: RECONCILE}).encode("utf-8")
