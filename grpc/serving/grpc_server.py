from concurrent import futures
import config
import more_utils

more_utils.set_logging_level(config.LOGGING_LEVEL)
import grpc

import signal
from serving.grpc_route import RouteGuideServicer
import serving.forecasting_pb2_grpc as forecasting_pb2_grpc
from more_utils.logging import configure_logger

LOGGER = configure_logger(logger_name="GRPC_Server", package_name=None)

class GRPCServer:
    def __init__(self, hostname, port) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self.executor = futures.ThreadPoolExecutor(max_workers=5)
        self.server = grpc.server(self.executor)
        self.servicer = RouteGuideServicer()
        forecasting_pb2_grpc.add_RouteGuideServicer_to_server(
            self.servicer, self.server
        )
        self.server.add_insecure_port(f"{hostname}:{port}")

        LOGGER.info(f"GRPC Server Started. Listening on {hostname}:{port}")

        self.server.start()
        self.server.wait_for_termination()

    def stop(self, signum, frame):
        LOGGER.info("Shutting down GRPC server...")
        self.executor.shutdown()
        self.server.stop(0)
        self.server.wait_for_termination()


if __name__ == '__main__':
    LOGGER.info(f"Starting IBM Forecasting GRPC server")
    GRPCServer(config.GRPC_HOST, config.GRPC_PORT)