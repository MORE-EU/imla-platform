import json
import sys

import serving.forecasting_pb2 as forecasting_pb2
import serving.forecasting_pb2_grpc as forecasting_pb2_grpc
from google.protobuf.json_format import MessageToDict, ParseDict

import grpc


def start_training(stub):
    response = stub.StartTraining(
        ParseDict(
            {
                "id": "1345667",
                "config": json.dumps(
                    {
                        "startDate": 1357678740000,
                        "endDate": 1389816000000,
                        "time_interval": "15m",
                        "targetColumn": ["active_power"],
                        "experiment": "WIND_POWER_ESTIMATION",
                    }
                ),
            },
            forecasting_pb2.TrainingInfo(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def get_progress(stub):
    response = stub.GetProgress(
        ParseDict(
            {"id": "1345667"},
            forecasting_pb2.JobID(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def get_specific_results(stub):
    response = stub.GetSpecificTargetResults(
        ParseDict(
            {"id": "1345667", "name": "active_power"},
            forecasting_pb2.Target(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def get_all_results(stub):
    response = stub.GetAllTargetsResults(
        ParseDict(
            {"id": "1345667"},
            forecasting_pb2.JobID(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def get_inference(stub):
    response = stub.GetInference(
        ParseDict(
            {"timestamp": 1345667, "model_name": "AdaptiveRandomForestClassifier"},
            forecasting_pb2.Timestamp(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def run(service):
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = forecasting_pb2_grpc.RouteGuideStub(channel)

        if service == "training":
            print("-------------- StartTraining --------------")
            start_training(stub)
        if service == "progress":
            print("-------------- GetProgress --------------")
            get_progress(stub)
        if service == "specific_results":
            print("-------------- GetSpecificTargetResults --------------")
            get_all_results(stub)
        if service == "all_results":
            print("-------------- GetAllTargetsResults --------------")
            get_all_results(stub)
        if service == "inference":
            print("-------------- GetInference --------------")
            get_inference(stub)


if __name__ == "__main__":
    run(sys.argv[1])
