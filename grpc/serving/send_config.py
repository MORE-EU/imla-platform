import argparse
import json
from more_utils.messaging import RabbitMQFactory
import yaml
import config
from validation import validate_host_and_port
from more_utils.logging import configure_logger

LOGGER = configure_logger(logger_name="GRPC_Server", package_name=None)

class ServerMessageHandler:
    def __init(self):
        self.message = None

    def handler(self, message):
        self.message = json.loads(message)

BROKER_CONFIG = {
    "broker_host": config.RABBITMQ_HOST,
    "broker_port": config.RABBITMQ_PORT,
    "broker_vhost": "/",
    "broker_request_queue": config.RABBITMQ_PRODUCER_QUEUE,
    "broker_response_queue": config.RABBITMQ_CONSUMER_QUEUE,
    "broker_delayed_exchange": "delay",
    "broker_user": config.RABBITMQ_USER,
    "broker_password": config.RABBITMQ_PASS,
}

def send_training_task(config_file):

    validate_host_and_port(config.RABBITMQ_HOST, config.RABBITMQ_PORT)
    rabbitmq_context = RabbitMQFactory.create_context(args=BROKER_CONFIG)

    with rabbitmq_context.client() as client:
        
        publisher = client.get_publisher()
        with open("configs/" + config_file) as fp:
            run_configs = yaml.safe_load(fp)
        
        publisher.publish(json.dumps(run_configs))

        receiver = client.get_consumer()
        message = receiver.receive(handler=ServerMessageHandler().handler, max_messages=1, timeout=None)
        message = message.decode("UTF-8")
        message = json.loads(message)
        LOGGER.info("Message Received: ", message)

