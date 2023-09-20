import os
import socket

import config
import more_utils

more_utils.set_logging_level(config.LOGGING_LEVEL)
import signal
import sys
import tempfile
from argparse import ArgumentParser

from more_utils.logging import configure_logger
from more_utils.messaging import RabbitMQFactory
from more_utils.persistence.modelardb import ModelarDB
from sail.telemetry import TracingClient

from forecasting_service.service import ForecastingService
from forecasting_service.validation import validate_host_and_port

LOGGER = configure_logger(logger_name="ForecastingService", package_name=None)

modelardb_configs = {
    "hostname": config.MODELARDB_HOSTNAME,
    "port": config.MODELARDB_PORT,
    "interface": config.MODELARDB_INTERFACE,
}

broker_configs = {
    "broker_host": config.RABBITMQ_HOST,
    "broker_port": config.RABBITMQ_PORT,
    "broker_vhost": "/",
    "broker_request_queue": config.RABBITMQ_CONSUMER_QUEUE,
    "broker_response_queue": config.RABBITMQ_PRODUCER_QUEUE,
    "broker_delayed_exchange": "delay",
    "broker_user": config.RABBITMQ_USER,
    "broker_password": config.RABBITMQ_PASS,
}


def signal_handler(sig, frame):
    print("Exiting Forecasting service...")
    sys.exit(0)


def run_service(data_dir):
    try:
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

        if config.OTLP_ENDPOINT:
            tracer = TracingClient(
                service_name=os.environ.get("POD_NAME")
                if os.environ.get("POD_NAME")
                else "ForecastingService",
                otlp_endpoint=config.OTLP_ENDPOINT,
            )
        else:
            LOGGER.info(f"Telemetry service is disabled.")
            tracer = None

        service = ForecastingService(
            modelardb_conn=modelardb_conn,
            message_broker=message_broker,
            data_dir=data_dir,
            tracer=tracer,
        )
        service.run()
    except KeyboardInterrupt:
        print(f"\n{service.name} terminated.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
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
