import numpy as np
from grpc import StatusCode

import serving.forecasting_pb2 as forecasting_pb2
import serving.forecasting_pb2_grpc as forecasting_pb2_grpc
from serving.send_config import send_training_task

class RouteGuideServicer(forecasting_pb2_grpc.RouteGuideServicer):
    def GetInference(self, request, context):
        # get the timestamp from the request and convert it to a datetime object
        # date = datetime.fromtimestamp(request.timestamp / 1000)
        model_name = request.model_name
        print("model_name: ", model_name)

        # Convert date to dataframe and set it as the index
        # date = pd.DataFrame({"timestamp": [date]})
        # date["timestamp"] = pd.to_datetime(date["timestamp"])
        # date = date.set_index("timestamp")

        # get the predictions for the given timestamp and assign to Any type
        # y_pred = predict(request.timestamp, date, model_name)

        send_training_task("run_configs_regression_wind_turbine.yaml")

        predictions = {}
        values = np.linspace(0, 1, 100, dtype=float)
        for index, value in enumerate(values):
            predictions[str(index)] = value

        if None:
            # return empty response if model not exist
            context.abort(StatusCode.INVALID_ARGUMENT, "Model does not exist")
        else:
            return forecasting_pb2.Inference(predictions=predictions)