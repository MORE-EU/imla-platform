import json
from datetime import datetime

import time
import ray
import os
from more_utils.time_series import TimeseriesFactory
from more_utils.logging import configure_logger
from ray.tune.utils.util import SafeFallbackEncoder
from forecasting_service.data_stream import DataStreamFactory

LOGGER = configure_logger(logger_name="ForecastingService", package_name=None)


class MessageHandler:
    def __init__(self):
        self.message = None

    def handler(self, message):
        self.message = json.loads(message)

    def get_message(self):
        return self.message


class BaseService:
    def __init__(self, name, modelardb_conn, message_broker, data_dir):
        self.name = name
        self.modelardb_conn = modelardb_conn
        self.message_broker = message_broker
        self.data_dir = data_dir

        self.client = message_broker.client()
        self.consumer = self.client.get_consumer()
        self.publisher = self.client.get_publisher()
        LOGGER.info("Connected to Message Broker.")

        self.ts_factory = TimeseriesFactory(source_db_conn=modelardb_conn)
        LOGGER.info("Connected to ModelarDB.")

    def create_experiment_directory(self, data_dir):
        exp_name = "ForecastingTask" + "_" + time.strftime("%d-%m-%Y_%H:%M:%S")
        exp_dir = os.path.join(data_dir, exp_name)
        os.umask(0)
        os.makedirs(exp_dir, mode=0o777, exist_ok=True)
        return exp_dir

    def log_config(self, config):
        LOGGER.info(
            "Data stream configs received:\n"
            + json.dumps(config, indent=2, cls=SafeFallbackEncoder)
        )

    def send_job_ack(self):
        self.publisher.publish(
            json.dumps({"STATUS": "ACCEPTED", "timestamp": datetime.now()}, default=str)
        )

    def publish_predictions(self, predictions):
        response_msg = {"predictions": predictions}
        with open(os.path.join(self.exp_dir, "response.json"), "w") as f:
            json.dump(response_msg, f, indent=2)

    def save_model_instance(self, model):
        model.save_model(os.path.join(self.exp_dir, "model"))

    def process_ts_batch(self, ts_batch, timestamp_col):
        LOGGER.info(f"Processing new data batch... ")
        max = ts_batch[timestamp_col].max()
        min = ts_batch[timestamp_col].min()
        LOGGER.info(f"Batch Received: From {min} to {max}")
        return True

    def process_time_series(self):
        LOGGER.info("Listening for incoming time-series task...")
        try:
            mh = MessageHandler()

            # Receive one task at a time from Message Broker
            self.consumer.receive(mh.handler, max_messages=1, timeout=None)

            # Send acknowlegment for the incoming task
            self.send_job_ack()

            # get message from handler
            run_configs = mh.get_message()
            self.log_config(run_configs["data_stream"])

            self.exp_dir = self.create_experiment_directory(self.data_dir)
            LOGGER.info(f"Experiment directory created: {self.exp_dir}")

            model = self.load_or_create_model(run_configs["sail"])

            data_stream = DataStreamFactory.create_data_stream(
                run_configs["data_stream"], self.ts_factory
            )
            data_session = data_stream.get_data_session()
            target, timestamp_col, fit_params = data_stream.get_training_params(
                run_configs["sail"]["steps"][-1]["name"]
            )

            predictions = {}
            for ts_batch in data_session:
                if data_stream.validate_batch(ts_batch):
                    prediction = self.process_ts_batch(
                        model, ts_batch, target, timestamp_col, fit_params
                    )
                    predictions.update(prediction)
                data_stream.wait()

            # save trained model instance
            if run_configs["save_model_after_training"]:
                self.save_model_instance(model)

            # publish predictions
            self.publish_predictions(predictions)

            LOGGER.info(
                f"Task finished successfully."
                + (
                    f" Model saved to {self.exp_dir}/model \n"
                    if run_configs["save_model_after_training"]
                    else ""
                )
            )

        except Exception as e:
            LOGGER.error(f"Error processing new request:")
            LOGGER.exception(e)
        finally:
            ray.shutdown()

    def run_forever(self, method, **kwargs):
        while True:
            method(**kwargs)

    def run(self):
        LOGGER.info(f"Service started: {self.name}")
