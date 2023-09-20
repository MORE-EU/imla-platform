from decouple import config


LOGGING_LEVEL = config("LOGGING_LEVEL", default="INFO")

MODELARDB_HOSTNAME = config("MODELARDB_HOSTNAME")
MODELARDB_PORT = config("MODELARDB_PORT", default=9999, cast=int)
MODELARDB_INTERFACE = config("MODELARDB_INTERFACE", default="arrow", cast=str)

RABBITMQ_USER = config("RABBITMQ_USER", cast=str)
RABBITMQ_PASS = config("RABBITMQ_PASS", cast=str)
RABBITMQ_HOST = config("RABBITMQ_HOST", default="localhost", cast=str)
RABBITMQ_PORT = config("RABBITMQ_PORT", default=5672, cast=int)
RABBITMQ_CONSUMER_QUEUE = config("RABBITMQ_CONSUMER_QUEUE")
RABBITMQ_PRODUCER_QUEUE = config("RABBITMQ_PRODUCER_QUEUE")

OTLP_ENDPOINT = config("OTLP_ENDPOINT", default=None)
