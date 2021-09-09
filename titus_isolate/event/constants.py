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
TASK_ID = "TITUS_TASK_INSTANCE_ID"

CONTAINER = "container"

# Handled Actions
# Docker
START = "start"
STARTS = "starts"
DIE = "die"
DIES = "dies"
# Internal
REBALANCE = "rebalance"
RECONCILE = "reconcile"
PREDICT_USAGE = "predict_usage"
# Batch
CONTAINER_BATCH = "container_batch"

CONTAINER_EVENTS = [START, DIE]
INTERNAL_EVENTS = [REBALANCE, RECONCILE, PREDICT_USAGE]
HANDLED_ACTIONS = CONTAINER_EVENTS + INTERNAL_EVENTS

REQUIRED_LABELS = [NAME]

SERVICE = "SERVICE"
BATCH = "BATCH"

REBALANCE_EVENT = json.dumps({ACTION: REBALANCE}).encode("utf-8")
RECONCILE_EVENT = json.dumps({ACTION: RECONCILE}).encode("utf-8")
PREDICT_USAGE_EVENT = json.dumps({ACTION: PREDICT_USAGE}).encode("utf-8")
