import json

ACTION = "Action"
ACTOR = "Actor"
ATTRIBUTES = "Attributes"
ID = "ID"
LOWERCASE_ID = "id"
NAME = "name"
REPO_DIGESTS = 'RepoDigests'
TIME = "time"
TYPE = "Type"

CONTAINER = "container"

# Handled Actions
# Docker
START = "start"
DIE = "die"
# Internal
REBALANCE = "rebalance"
RECONCILE = "reconcile"
OVERSUBSCRIBE = "oversubscribe"

HANDLED_ACTIONS = [START, DIE, REBALANCE, RECONCILE, OVERSUBSCRIBE]

WORKLOAD_TYPE_LABEL_KEY = "com.netflix.titus.workload.type"
REQUIRED_LABELS = [NAME, WORKLOAD_TYPE_LABEL_KEY]

STATIC = "static"
BURST = "burst"
WORKLOAD_TYPES = [STATIC, BURST]

SERVICE = "SERVICE"
BATCH = "BATCH"

REBALANCE_EVENT = json.dumps({ACTION: REBALANCE}).encode("utf-8")
RECONCILE_EVENT = json.dumps({ACTION: RECONCILE}).encode("utf-8")
OVERSUBSCRIBE_EVENT = json.dumps({ACTION: OVERSUBSCRIBE}).encode("utf-8")
