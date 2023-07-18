from pyarrow import flight
import sys

def query_table(flight_client, table_name, limit=10):
    ticket = flight.Ticket(f"SELECT * FROM {table_name} LIMIT {limit}")
    flight_stream_reader = flight_client.do_get(ticket)

    for flight_stream_chunk in flight_stream_reader:
        record_batch = flight_stream_chunk.data
        pandas_data_frame = record_batch.to_pandas()
        print(pandas_data_frame)

# Main Function.
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} host table [limit]")
        sys.exit(1)

    flight_client = flight.FlightClient(f"grpc://{sys.argv[1]}:9999")
    table_name = sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv)==4 else 10

    query_table(flight_client, table_name, limit)
