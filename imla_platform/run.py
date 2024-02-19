import os

import config
import more_utils
import json

more_utils.set_logging_level(config.LOGGING_LEVEL)
import signal
import sys
import tempfile
from argparse import ArgumentParser

from more_utils.logging import configure_logger
from more_utils.messaging import RabbitMQFactory
from more_utils.persistence.modelardb import ModelarDB


from imla_platform.service import IMLAPlatform
from imla_platform.validation import validate_host_and_port

LOGGER = configure_logger(logger_name="IMLAPlatform", package_name=None)

modelardb_configs = {
    "hostname": config.MODELARDB_HOSTNAME,
    "port": config.MODELARDB_PORT,
    "interface": config.MODELARDB_INTERFACE,
}

broker_configs = {
    "broker_host": config.RABBITMQ_HOST,
    "broker_port": config.RABBITMQ_PORT,
    "broker_vhost": "/",
    "broker_request_queue": config.FORECASTING_CONSUMER_QUEUE,
    "broker_response_queue": config.FORECASTING_PRODUCER_QUEUE,
    "broker_delayed_exchange": "delay",
    "broker_user": config.RABBITMQ_USER,
    "broker_password": config.RABBITMQ_PASS,
}


def signal_handler(sig, frame):
    print("Exiting Forecasting service...")
    sys.exit(0)


def run_service(data_dir):
    try:
        LOGGER.info(
            "ModelarDB configs received:\n"
            + json.dumps(modelardb_configs, indent=2)
        )

        LOGGER.info(
            "Broker configs received:\n"
            + json.dumps(broker_configs, indent=2)
        )

        validate_host_and_port(config.MODELARDB_HOSTNAME, config.MODELARDB_PORT)
        modelardb_conn = ModelarDB.connect(**modelardb_configs)
        LOGGER.info(
            f"Connected to ModelarDB at {config.MODELARDB_HOSTNAME}:{config.MODELARDB_PORT}"
        )

        validate_host_and_port(config.RABBITMQ_HOST, config.RABBITMQ_PORT)
        message_broker = RabbitMQFactory.create_context(args=broker_configs)
        LOGGER.info(
            f"Connected to Message Broker at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT}"
        )

        service = IMLAPlatform(
            modelardb_conn=modelardb_conn,
            message_broker=message_broker,
            data_dir=data_dir,
        )
        service.run()
    except KeyboardInterrupt:
        print(f"\n{service.name} terminated.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = ArgumentParser()
    parser.add_argument(
        "--data_dir",
        help="Path to data directory",
        type=str,
        required=False,
    )
    args = parser.parse_args()
    data_dir = args.data_dir
    if not data_dir:
        data_dir = tempfile.mkdtemp()
    os.makedirs(data_dir, exist_ok=True)
    run_service(data_dir)
