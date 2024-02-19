import json
import os
import time
from datetime import datetime

import ray
from more_utils.logging import configure_logger
from more_utils.time_series import TimeseriesFactory
from ray.tune.utils.util import SafeFallbackEncoder
from sail.telemetry import DummySpan, TracingClient

from imla_platform.data_stream import DataStreamFactory
from imla_platform.validation import validate_address

LOGGER = configure_logger(logger_name="IMLA Platform", package_name=None)

SERVICE_NAME = (
    os.environ.get("POD_NAME") if os.environ.get("POD_NAME") else "IMLAPlatform"
)


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

        self.ts_factory = TimeseriesFactory(source_db_conn=modelardb_conn)

    def create_client(self):
        return self.message_broker.client()

    def create_experiment_directory(self, data_dir):
        exp_name = "IMLATask" + "_" + time.strftime("%d-%m-%Y_%H:%M:%S")
        exp_dir = os.path.join(data_dir, exp_name)
        os.umask(0)
        os.makedirs(exp_dir, mode=0o777, exist_ok=True)
        return exp_dir, exp_name

    def log_config(self, config):
        LOGGER.info(
            "Data stream configs received:\n"
            + json.dumps(config, indent=2, cls=SafeFallbackEncoder)
        )

    def send_job_response(self, job_id, status, target, response):
        message = {
            "job_id": job_id,
            "status": status,
            "timestamp": datetime.now(),
            "service": SERVICE_NAME,
            "experiment": self.exp_name,
            "target": target,
            "response": response,
        }
        self.create_client().get_publisher().publish(json.dumps(message, default=str))

    def publish_predictions(self, predictions):
        response_msg = {"predictions": predictions}
        with open(os.path.join(self.exp_dir, "response.json"), "w") as f:
            json.dump(response_msg, f, indent=2)

    def publish_evaluation(self, evaluation):
        response_msg = {"evaluation": evaluation}
        with open(os.path.join(self.exp_dir, "evaluation.json"), "w") as f:
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

    def trace(self, tracer, span_name, current_span=False, *args, **kwargs):
        if tracer is not None:
            if current_span:
                return tracer.trace_as_current_span(span_name, *args, **kwargs)
            else:
                return tracer.trace(span_name, *args, **kwargs)
        else:
            return DummySpan()

    def process_time_series(self):
        LOGGER.info("Listening for incoming time-series task...")
        try:
            mh = MessageHandler()

            # Receive one task at a time from Message Broker
            self.create_client().get_consumer().receive(
                mh.handler, max_messages=1, timeout=None
            )

            # get message from handler
            run_configs = mh.get_message()
            self.log_config(run_configs["data_stream"])

            self.exp_dir, self.exp_name = self.create_experiment_directory(
                self.data_dir
            )
            LOGGER.info(f"Experiment directory created: {self.exp_dir}")

            # Send acknowlegment for the incoming task
            self.send_job_response(
                job_id=run_configs["job_id"],
                status="ACCEPTED",
                target=run_configs["data_stream"]["target"],
                response="Task Accepted by Forecasting Service.",
            )

            tracer = None
            tracer_configs = run_configs["sail"]["tracer"]
            if tracer_configs:
                otlp_endpoint = tracer_configs["otlp_endpoint"]
                if validate_address(otlp_endpoint, throw_exception=False):
                    tracer = TracingClient(
                        service_name=SERVICE_NAME,
                        otlp_endpoint=otlp_endpoint,
                    )
                    LOGGER.info(
                        f"Telemetry service is enabled. Check traces at: {tracer_configs['web_interface']}/search&service={SERVICE_NAME}"
                    )
                else:
                    LOGGER.error(
                        f"Telemetry service at {otlp_endpoint} is unreachable."
                    )
            else:
                LOGGER.info(f"Telemetry service is disabled.")

            with self.trace(tracer, self.exp_name, current_span=True):
                with self.trace(tracer, "PIPELINE_LOAD"):
                    model = self.load_or_create_model(run_configs["sail"], tracer)

                data_stream = DataStreamFactory.create_data_stream(
                    run_configs["data_stream"], self.ts_factory
                )
                data_session = data_stream.get_data_session()
                target, timestamp_col, fit_params = data_stream.get_training_params(
                    run_configs["sail"]["steps"][-1]["name"]
                )

                with self.trace(tracer, "PIPELINE_TRAIN", current_span=True):
                    predictions = {}
                    for ts_batch in data_session:
                        if data_stream.validate_batch(ts_batch):
                            ts_batch = data_stream.apply_granularity(ts_batch)
                            prediction = self.process_ts_batch(
                                model,
                                ts_batch,
                                target,
                                timestamp_col,
                                fit_params,
                            )
                            predictions.update(prediction)
                        data_stream.wait()

                # save trained model instance
                if run_configs["save_model_after_training"]:
                    with self.trace(tracer, "PIPELINE_PERSIST-model"):
                        self.save_model_instance(model)

                # publish predictions
                with self.trace(tracer, "PIPELINE_PUBLISH-predictions"):
                    self.publish_predictions(predictions)

                # publish evaluation
                with self.trace(tracer, "PIPELINE_PUBLISH-evaluations"):
                    self.publish_evaluation(model.metrics)

                self.send_job_response(
                    job_id=run_configs["job_id"],
                    status="COMPLETED",
                    target=run_configs["data_stream"]["target"],
                    response="Task finished successfully.",
                )

                LOGGER.info(
                    f"Task finished successfully."
                    + (
                        f" Model saved to {self.exp_dir}/model \n"
                        if run_configs["save_model_after_training"]
                        else ""
                    )
                )

        except Exception as e:
            if run_configs:
                self.send_job_response(
                    job_id=run_configs["job_id"],
                    status="ERROR",
                    target=run_configs["data_stream"]["target"],
                    response=str(e),
                )
            LOGGER.error(f"Error processing new request:")
            LOGGER.exception(e)
        finally:
            ray.shutdown()

    def run_forever(self, method, **kwargs):
        while True:
            method(**kwargs)

    def run(self):
        LOGGER.info(f"Service started: {self.name}")
