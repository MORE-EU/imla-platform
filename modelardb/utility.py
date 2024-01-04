import pyarrow

from pyarrow import flight

import os

def do_action(flight_client, action_type, action_body_str):
    action_body = str.encode(action_body_str)
    action = pyarrow.flight.Action(action_type, action_body)
    response = flight_client.do_action(action)

    print(list(response))


if __name__ == "__main__":
    # Connect to the manager node and create the table that should be used for ingestion.
    manager_client = flight.FlightClient(f"grpc://{os.environ['MODELARDB_MANAGER_PORT']}:9998")

    do_action(
        manager_client,
        "CommandStatementUpdate",
        "CREATE MODEL TABLE windmill(timestamp TIMESTAMP, temperature FIELD, wind_speed FIELD)",
    )
