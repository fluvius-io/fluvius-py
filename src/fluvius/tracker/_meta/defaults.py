from fluvius.data import config

DEBUG = False

TRACKER_DSN = config.DB_DSN
TRACKER_DATA_SCHEMA = "fluvius-tracker"
WORKER_JOB_TABLE = "job-tracker"
JOB_RELATION_TABLE = "job-relation"
ARQ_WORKER_TABLE = "arq-worker"
COLLECT_TRACEBACK = True
