import os
os.environ["TUNE_DISABLE_SIGINT_HANDLER"] = "1"
import signal
import sys

import config
from more_utils.messaging import RabbitMQFactory
from more_utils.persistence.modelardb import ModelarDB

from forecasting_service.service import ForecastingService

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
    print('Exiting Forecasting service...')
    sys.exit(0)

def run_service():
    try:
        modelardb_conn = ModelarDB.connect(**modelardb_configs)
        message_broker = RabbitMQFactory.create_context(args=broker_configs)
        service = ForecastingService(
            modelardb_conn=modelardb_conn,
            message_broker=message_broker,
            logging_level=config.LOGGING_LEVEL,
            data_dir=config.DATA_DIR,
        )
        service.run()
    except KeyboardInterrupt:
        print(f"\n{service.name} terminated.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    run_service()
