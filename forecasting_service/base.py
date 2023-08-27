import json
from datetime import datetime
from time import sleep
import time
import ray
import os
from more_utils.time_series import TimeseriesFactory
from more_utils.logging import configure_logger
from ray.tune.utils.util import SafeFallbackEncoder

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

        self._ts_factory = TimeseriesFactory(source_db_conn=modelardb_conn)
        LOGGER.info("Connected to ModelarDB.")

    def create_experiment_directory(self, data_dir):
        exp_name = "ForecastingTask" + "_" + time.strftime("%d-%m-%Y_%H:%M:%S")
        exp_dir = os.path.join(data_dir, exp_name)
        os.umask(0)
        os.makedirs(exp_dir, mode=0o777, exist_ok=True)
        return exp_dir

    def get_query_session(self, configs):
        time_series = self._ts_factory.create_time_series(
            model_table=configs["model_table"],
            from_date=configs["from_date"],
            to_date=configs["to_date"],
            limit=configs["data_limit"],
        )

        self.columns = time_series.columns
        target = configs["target"]
        features = list(set(self.columns) - set([target]))
        query_session = time_series.fetch_next(batch_size=configs["data_batch_size"])
        LOGGER.info(
            f"Query session created. Time-series found with features: {features} and target: {target}"
        )

        return query_session

    def get_training_params(self, configs):
        fit_params = {}
        if (
            configs["sail"]["incremental_training"]
            and configs["time_series"]["classes"]
        ):
            estimator_ref = configs["sail"]["steps"][-1]["name"]
            fit_params[f"{estimator_ref}__classes"] = configs["time_series"]["classes"]

        target = configs["time_series"]["target"]
        timestamp_col = configs["time_series"]["timestamp_col"]

        return target, timestamp_col, fit_params

    def log_config(self, config):
        LOGGER.info(
            "Time-series configs received:\n"
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

    def ts_batch_validation(self, ts_batch, columns):
        if ts_batch.shape[0] <= 0:
            LOGGER.error(
                f"Empty Time-series batch received. Ignoring bad time-series batch."
            )
            return False
        elif list(ts_batch.columns) != columns:
            LOGGER.error(
                f"Missing features in a current batch: {list(set(columns).intersection(set(ts_batch.columns)))}. Ignoring bad time-series batch."
            )
            return False

        return True

    def process_ts_batch(self, ts_batch, timestamp_col):
        LOGGER.info(f"Processing new time-series batch... ")
        if not self.ts_batch_validation(ts_batch, self.columns):
            return False

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
            self.log_config(run_configs["time_series"])

            self.exp_dir = self.create_experiment_directory(self.data_dir)
            LOGGER.info(f"Experiment directory created: {self.exp_dir}")

            model = self.load_or_create_model(run_configs["sail"])
            query_session = self.get_query_session(run_configs["time_series"])
            target, timestamp_col, fit_params = self.get_training_params(run_configs)

            predictions = {}
            for ts_batch in query_session:
                predictions.update(
                    self.process_ts_batch(
                        model, ts_batch, target, timestamp_col, fit_params
                    )
                )
                sleep(run_configs["time_series"]["data_ingestion_freq"])

            # save trained model instance
            self.save_model_instance(model)

            # publish predictions
            self.publish_predictions(predictions)

            LOGGER.info(
                f"Task finished successfully. Model saved to {self.exp_dir}/model \n"
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
