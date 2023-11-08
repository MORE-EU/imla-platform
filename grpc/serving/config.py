from decouple import config

LOGGING_LEVEL = config("LOGGING_LEVEL", default="INFO")

RABBITMQ_USER = config("RABBITMQ_USER", cast=str)
RABBITMQ_PASS = config("RABBITMQ_PASS", cast=str)
RABBITMQ_HOST = config("RABBITMQ_HOST", default="localhost", cast=str)
RABBITMQ_PORT = config("RABBITMQ_PORT", default=5672, cast=int)
RABBITMQ_GRPC_CONSUMER_QUEUE = config("RABBITMQ_GRPC_CONSUMER_QUEUE")
RABBITMQ_GRPC_PRODUCER_QUEUE = config("RABBITMQ_GRPC_PRODUCER_QUEUE")

GRPC_HOST = config("GRPC_HOST", default="localhost", cast=str)
GRPC_PORT = config("GRPC_PORT", default=50051, cast=int)
