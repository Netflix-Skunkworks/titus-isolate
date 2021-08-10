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
PREDICT_USAGE = "predict_usage"

HANDLED_ACTIONS = [START, DIE, REBALANCE, RECONCILE, PREDICT_USAGE]

WORKLOAD_TYPE_LABEL_KEY = "com.netflix.titus.workload.type"
REQUIRED_LABELS = [NAME, WORKLOAD_TYPE_LABEL_KEY]

STATIC = "static"
BURST = "burst"
WORKLOAD_TYPES = [STATIC, BURST]

SERVICE = "SERVICE"
BATCH = "BATCH"

REBALANCE_EVENT = json.dumps({ACTION: REBALANCE}).encode("utf-8")
RECONCILE_EVENT = json.dumps({ACTION: RECONCILE}).encode("utf-8")
PREDICT_USAGE_EVENT = json.dumps({ACTION: PREDICT_USAGE}).encode("utf-8")
