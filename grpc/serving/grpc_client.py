import sys
sys.path.append("../") 
import grpc
import serving.forecasting_pb2 as forecasting_pb2
import serving.forecasting_pb2_grpc as forecasting_pb2_grpc
from google.protobuf.json_format import MessageToDict, ParseDict


def get_inference(stub):
    response = stub.GetInference(
        ParseDict(
            {"timestamp": 134566, "model_name": "AdaptiveRandomForestClassifier"},
            forecasting_pb2.Timestamp(),
        )
    )

    print(f"Received message - {MessageToDict(response)}")


def run():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = forecasting_pb2_grpc.RouteGuideStub(channel)
        print("-------------- GetInference --------------")
        get_inference(stub)


if __name__ == "__main__":
    run()
