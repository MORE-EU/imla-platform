import json
import os
import threading
from datetime import datetime

import numpy as np
import serving.forecasting_pb2 as forecasting_pb2
import serving.forecasting_pb2_grpc as forecasting_pb2_grpc
import yaml
from more_utils.logging import configure_logger

from grpc import StatusCode

LOGGER = configure_logger(logger_name="GRPC_Server", package_name=None)

EXPERIMENT_TO_CONFIG_FILE = {
    "WIND_POWER_ESTIMATION": "configs/run_configs_regression_wind_turbine.yaml"
}

# Define a shared variable to hold the object returned from the background task
shared_lock = threading.Lock()


class ServerMessageHandler:
    def __init__(self):
        self.message = None

    def handler(self, message):
        self.message = json.loads(message)


class RouteGuideServicer(forecasting_pb2_grpc.RouteGuideServicer):
    def __init__(self, rabbitmq_context, data_dir):
        self.jobs = {}
        self.rabbitmq_context = rabbitmq_context
        self.data_dir = data_dir

    def process_reponse(self):
        with self.rabbitmq_context.client() as client:
            receiver = client.get_consumer()
            while True:
                message = receiver.receive(
                    handler=ServerMessageHandler().handler, max_messages=1, timeout=None
                )
                message = message.decode("UTF-8")
                message = json.loads(message)

                with shared_lock:
                    job_id = message["job_id"]
                    if job_id in self.jobs:
                        target = message["target"]
                        LOGGER.info(
                            f"Message Received: {message} for job_id: {job_id} and target: {target}"
                        )
                        target_data = self.jobs[job_id][target]
                        if "COMPLETED" == message["status"]:
                            target_data["status"] = "done"
                        target_data["timestamp"] = message["timestamp"]
                        target_data["service"] = message["service"]
                        target_data["experiment"] = message["experiment"]
                        target_data["response"] = message["response"]
                    else:
                        LOGGER.error(f"Invalid Job Id received. Message: {message}")

    def StartTraining(self, request, context):
        LOGGER.info(f"[StartTraining] - Request received with job id:{request.id}.")

        # Read the config from the request
        configs = json.loads(request.config)

        # for each target column, create a status with waiting
        self.jobs[request.id] = {}
        for target in configs["targetColumn"]:
            self.jobs[request.id] = {target: {"status": "waiting"}}

            with open(EXPERIMENT_TO_CONFIG_FILE[configs["experiment"]]) as fp:
                run_configs = yaml.safe_load(fp)

            # append parameters
            run_configs["job_id"] = request.id
            run_configs["data_stream"]["target"] = target
            run_configs["data_stream"]["time_interval"] = configs["time_interval"]
            run_configs["data_stream"]["from_date"] = str(
                datetime.fromtimestamp(configs["startDate"] / 1000)
            )
            run_configs["data_stream"]["to_date"] = str(
                datetime.fromtimestamp(configs["endDate"] / 1000)
            )

            with self.rabbitmq_context.client() as client:
                publisher = client.get_publisher()
                publisher.publish(json.dumps(run_configs))

            self.jobs[request.id][target]["status"] = "processing"

        return forecasting_pb2.Status(id=request.id, status="started")

    def GetProgress(self, request, context):
        """
        Get progress for a specific job
        Return: The job id and the status of each target column
        """
        job_id = request.id

        if job_id in self.jobs:
            # Create a Struct message
            data = {}

            # Add the status of each target column to the struct
            for target, target_data in self.jobs[job_id].items():
                data[target] = target_data["status"]

            return forecasting_pb2.Progress(id=job_id, data=data)
        else:
            # return empty response
            context.abort(StatusCode.INVALID_ARGUMENT, "Not a valid job id")

    def GetSpecificTargetResults(self, request, context):
        """
        Get the results for a specific target column
        Return: The predictions and evaluation metrics for each model
        """
        target = request.name
        job_id = request.id

        if job_id in self.jobs:
            if target in self.jobs[job_id]:
                target_data = self.jobs[job_id][target]
                if target_data["status"] == "done":
                    data = {}
                    # assign the prediction results for each model
                    data["SAILModel"] = forecasting_pb2.Predictions(
                        predictions=self.get_predictions(target_data),
                        evaluation={"MSE": 345.457},
                    )

                    return forecasting_pb2.Results(target=target, metrics=data)
                else:
                    # return empty response
                    context.abort(
                        StatusCode.INVALID_ARGUMENT, "Task has not finished yet"
                    )
        else:
            # return empty response
            context.abort(
                StatusCode.INVALID_ARGUMENT, "Not a valid job id or target column"
            )

    def GetAllTargetsResults(self, request, context):
        """
        Get the results for all target columns
        Return: The predictions and evaluation metrics for each model for each target column
        """
        job_id = request.id
        # create an empty response - array of dictionaries where each dictionary is a target column
        all_results = forecasting_pb2.AllResults()

        if job_id in self.jobs:
            data = {}
            for target, target_data in self.jobs[job_id].items():
                data[target] = {}

                if target_data["status"] == "done":
                    data[target]["SAILModel"] = forecasting_pb2.Predictions(
                        predictions=self.get_predictions(target_data),
                        evaluation={"MSE": 345.457},
                    )

                # add the target column and its results to the response
                all_results.results.append(
                    forecasting_pb2.Results(target=target, metrics=data[target])
                )
            return all_results
        else:
            # return empty response
            context.abort(StatusCode.INVALID_ARGUMENT, "Not a valid job id")

    def get_predictions(self, target_data):
        service = target_data["service"]
        experiment_name = target_data["experiment"]

        with open(
            os.path.join(self.data_dir, service, experiment_name, "response.json")
        ) as output:
            response = json.load(output)
            predictions = {
                timestamp: float(value)
                for timestamp, value in response["predictions"].items()
            }
            return predictions

    # def GetInference(self, request, context):
    #   # get the timestamp from the request and convert it to a datetime object
    #   date = datetime.fromtimestamp(request.timestamp / 1000)
    #   model_name = request.model_name

    #   # Convert date to dataframe and set it as the index
    #   date = pd.DataFrame({'timestamp': [date]})
    #   date['timestamp'] = pd.to_datetime(date['timestamp'])
    #   date = date.set_index('timestamp')

    #   # get the predictions for the given timestamp and assign to Any type
    #   y_pred = predict(request.timestamp, date, model_name)

    #   if y_pred is None:
    #     # return empty response if model not exist
    #     context.abort(StatusCode.INVALID_ARGUMENT, "Model does not exist")
    #   else:
    #     return forecasting_pb2.Inference(predictions=y_pred)
