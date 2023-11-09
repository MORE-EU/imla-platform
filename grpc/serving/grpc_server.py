import threading
from concurrent import futures

import config
import more_utils

more_utils.set_logging_level(config.LOGGING_LEVEL)
import json
import os
import signal
from argparse import ArgumentParser

import serving.forecasting_pb2_grpc as forecasting_pb2_grpc
from more_utils.logging import configure_logger
from more_utils.messaging import RabbitMQFactory
from serving.grpc_route import RouteGuideServicer
from validation import validate_host_and_port

import grpc

BROKER_CONFIG = {
    "broker_host": config.RABBITMQ_HOST,
    "broker_port": config.RABBITMQ_PORT,
    "broker_vhost": "/",
    "broker_request_queue": config.RABBITMQ_GRPC_CONSUMER_QUEUE,
    "broker_response_queue": config.RABBITMQ_GRPC_PRODUCER_QUEUE,
    "broker_delayed_exchange": "delay",
    "broker_user": config.RABBITMQ_USER,
    "broker_password": config.RABBITMQ_PASS,
}
LOGGER = configure_logger(logger_name="GRPC_Server", package_name=None)


class GRPCServer:
    def __init__(self, hostname, port, data_dir, config_dir) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self.log_config(BROKER_CONFIG)

        validate_host_and_port(config.RABBITMQ_HOST, config.RABBITMQ_PORT)
        rabbitmq_context = RabbitMQFactory.create_context(args=BROKER_CONFIG)
        LOGGER.info(
            f"Connected to Message Broker at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT}"
        )

        self.executor = futures.ThreadPoolExecutor(max_workers=5)
        self.server = grpc.server(self.executor)
        self.servicer = RouteGuideServicer(
            rabbitmq_context=rabbitmq_context, data_dir=data_dir, config_dir=config_dir
        )
        forecasting_pb2_grpc.add_RouteGuideServicer_to_server(
            self.servicer, self.server
        )
        self.server.add_insecure_port(f"{hostname}:{port}")

        # Start response processor
        self.thread = threading.Thread(target=self.servicer.process_reponse)
        self.thread.start()

        LOGGER.info(f"GRPC Server Started. Listening on {hostname}:{port}")

        # Start GRPC Server
        self.server.start()
        self.server.wait_for_termination()

    def stop(self, signum, frame):
        LOGGER.info("Shutting down GRPC server...")
        self.executor.shutdown()
        self.server.stop(0)
        self.server.wait_for_termination()

    def log_config(self, config):
        LOGGER.info("Broker configs:\n" + json.dumps(config, indent=2))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--data_dir",
        help="Path to forecasting data directory",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--config_dir",
        help="Path to forecasting config directory",
        type=str,
        required=True,
    )

    args = parser.parse_args()
    data_dir = args.data_dir
    config_dir = args.config_dir
    os.makedirs(data_dir, exist_ok=True)

    LOGGER.info(f"Starting IBM Forecasting GRPC server")
    GRPCServer(config.GRPC_HOST, config.GRPC_PORT, data_dir, config_dir)
