from decouple import config
import tempfile

LOGGING_LEVEL = config("LOGGING_LEVEL", default="INFO")

MODELARDB_HOSTNAME = config("MODELARDB_HOSTNAME")
MODELARDB_PORT = config("MODELARDB_PORT", default=9999, cast=int)
MODELARDB_INTERFACE = config("MODELARDB_INTERFACE", default="arrow", cast=str)
MODELARDB_DATA_BATCH_SIZE = config("MODELARDB_DATA_BATCH_SIZE", default=50, cast=int)
MODELARDB_INGESTION_FREQUENCY = config(
    "MODELARDB_INGESTION_FREQUENCY", default=0, cast=int
)
DATA_DIR = config("DATA_DIR", default="", cast=str)
if DATA_DIR == "":
    DATA_DIR = tempfile.mkdtemp()

RABBITMQ_USER = config("RABBITMQ_USER", cast=str)
RABBITMQ_PASS = config("RABBITMQ_PASS", cast=str)
RABBITMQ_HOST = config("RABBITMQ_HOST", default="localhost", cast=str)
RABBITMQ_PORT = config("RABBITMQ_PORT", default=5672, cast=int)
RABBITMQ_CONSUMER_QUEUE = config("RABBITMQ_CONSUMER_QUEUE")
RABBITMQ_PRODUCER_QUEUE = config("RABBITMQ_PRODUCER_QUEUE")
