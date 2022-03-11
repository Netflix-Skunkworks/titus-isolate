import json

# Docker Event constants. You can see these in action by watching
# docker events --format '{{json .}}'
# on a titus agent as containers start
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
# The above are stock docker string constants, the below are custom docker labels (attributes)
# set by the titus executor
TASK_ID = "titus.task_id"

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
