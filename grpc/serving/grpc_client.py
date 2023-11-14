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
                        "startDate": 1536451202000,
                        "endDate": 1536453200000,
                        "time_interval": "2S",
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

def save_model(stub):
    response = stub.SaveModel(
        ParseDict(
            {"model_type": "SAIL_AutoML", "model_name": "SAILModel", "target": "active_power"},
            forecasting_pb2.ModelInfo(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def get_inference(stub):
    response = stub.GetInference(
        ParseDict(
            {"timestamp": 1345667, "model_name": "SAILModel"},
            forecasting_pb2.Timestamp(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def run(service):
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("83.212.75.52:31051") as channel:
        stub = forecasting_pb2_grpc.RouteGuideStub(channel)

        if service == "training":
            print("-------------- StartTraining --------------")
            start_training(stub)
        elif service == "progress":
            print("-------------- GetProgress --------------")
            get_progress(stub)
        elif service == "specific_results":
            print("-------------- GetSpecificTargetResults --------------")
            get_all_results(stub)
        elif service == "all_results":
            print("-------------- GetAllTargetsResults --------------")
            get_all_results(stub)
        elif service == "save":
            print("-------------- GetAllTargetsResults --------------")
            save_model(stub)
        # elif service == "inference":
        #     print("-------------- GetInference --------------")
        #     get_inference(stub)
        else:
            print("-------------- Error: Invalid service name. --------------")


if __name__ == "__main__":
    run(sys.argv[1])
