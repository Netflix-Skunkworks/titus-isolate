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
START = "start"

CPU_LABEL_KEY = "com.netflix.titus.cpu"
WORKLOAD_TYPE_LABEL_KEY = "com.netflix.titus.workload.type"
REQUIRED_LABELS=[CPU_LABEL_KEY, WORKLOAD_TYPE_LABEL_KEY]

STATIC = "static"
BURST = "burst"
WORKLOAD_TYPES = [STATIC, BURST]
