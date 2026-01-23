from fluvius.data import config

DB_DSN      = config.DB_DSN
DB_SCHEMA   = "fluvius_navis"

DOMAIN_NAMESPACE = "process"
WORKFLOW_REPOSITORIES = []
WORKFLOW_RESOURCES = [] # All resources are allowed, otherwise a list of resource names

WORKER_NAMESPACE = "default-worker"