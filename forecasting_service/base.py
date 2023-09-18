import json
import os
import time
from datetime import datetime

import config
import ray
from more_utils.logging import configure_logger
from more_utils.time_series import TimeseriesFactory
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
    def __init__(self, name, modelardb_conn, message_broker, data_dir, tracer):
        self.name = name
        self.modelardb_conn = modelardb_conn
        self.message_broker = message_broker
        self.data_dir = data_dir
        self.tracer = tracer

        self.client = message_broker.client()
        self.consumer = self.client.get_consumer()
        self.publisher = self.client.get_publisher()
        LOGGER.info(
            f"Connected to Message Broker at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT}"
        )

        self.ts_factory = TimeseriesFactory(source_db_conn=modelardb_conn)
        modelardb_conn.create_session().close()
        LOGGER.info(
            f"Connected to ModelarDB at {config.MODELARDB_HOSTNAME}:{config.MODELARDB_PORT}"
        )

        # tracer configs
        self.tracer.create_instance("ForecastingService")

    def create_experiment_directory(self, data_dir):
        exp_name = "ForecastingTask" + "_" + time.strftime("%d-%m-%Y_%H:%M:%S")
        exp_dir = os.path.join(data_dir, exp_name)
        os.umask(0)
        os.makedirs(exp_dir, mode=0o777, exist_ok=True)
        return exp_dir, exp_name

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
        LOGGER.debug(f"Processing new data batch... ")

        if timestamp_col:
            max = ts_batch[timestamp_col].max()
            min = ts_batch[timestamp_col].min()
            LOGGER.debug(f"Batch Received: From {min} to {max}. Size: {len(ts_batch)}")
        else:
            LOGGER.debug(f"Batch Received. Size: {len(ts_batch)}")

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

            self.exp_dir, exp_name = self.create_experiment_directory(self.data_dir)
            LOGGER.info(f"Experiment directory created: {self.exp_dir}")

            with self.tracer.trace_as_current(exp_name):
                with self.tracer.trace("Pipeline-load"):
                    model = self.load_or_create_model(run_configs["sail"])

                data_stream = DataStreamFactory.create_data_stream(
                    run_configs["data_stream"], self.ts_factory
                )
                data_session = data_stream.get_data_session()
                target, timestamp_col, fit_params = data_stream.get_training_params(
                    run_configs["sail"]["steps"][-1]["name"]
                )

                with self.tracer.trace("Pipeline-train"):
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
                    with self.tracer.trace("Pipeline-persist"):
                        self.save_model_instance(model)

                # publish predictions
                with self.tracer.trace("Pipeline-publish"):
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
