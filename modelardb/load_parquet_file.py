import sys
import pyarrow as pa
import pyarrow
import pyarrow.parquet as pq
from pyarrow import parquet
from pyarrow import flight


# Helper Functions.
def table_exists(flight_client, table_name):
    tables = map(lambda flight: flight.descriptor.path, flight_client.list_flights())
    return [bytes(table_name, "UTF-8")] in tables


def create_model_table(flight_client, table_name, schema, error_bound):
    # Construct the CREATE MODEL TABLE string.
    columns = []
    for field in schema:
        if field.type == pyarrow.timestamp("ms"):
            columns.append(f"{field.name} TIMESTAMP")
        elif field.type == pyarrow.float32():
            columns.append(f"{field.name} FIELD({error_bound})")
        elif field.type == pyarrow.string():
            columns.append(f"{field.name} TAG")
        else:
            raise ValueError(f"Unsupported Data Type: {field.type}")

    sql = f"CREATE MODEL TABLE {table_name} ({', '.join(columns)})"

    # Execute the CREATE MODEL TABLE command.
    action = flight.Action("CommandStatementUpdate", str.encode(sql))
    results = flight_client.do_action(action)
    if results:
        print(next(results))
    else:
        print(f"Table: {table_name} created Successfully.")

def read_parquet_file_or_folder(path):
    # Read Apache Parquet file or folder.
    arrow_table = parquet.read_table(path)

    # Ensure the schema only uses supported features.
    columns = []
    column_names = []
    for field in arrow_table.schema:
        # Ensure that none of the field names contain whitespace.
        safe_name = field.name.replace(" ", "_")
        column_names.append(safe_name)

        # Ensure all fields are float32 as float64 are not supported.
        if field.type == pyarrow.float64():
            columns.append((safe_name, pyarrow.float32()))
        elif field.type == pyarrow.int64():
            columns.append((safe_name, pyarrow.float32()))
        elif field.name in ["pickup_datetime","dropoff_datetime","datetime"]:
            columns.append((field.name, pyarrow.timestamp("ms")))
        else:
            columns.append((safe_name, field.type))

    safe_schema = pyarrow.schema(columns)

    # Rename columns to remove whitespaces and cast them to remove float64.
    arrow_table = arrow_table.rename_columns(column_names)
    return arrow_table.cast(safe_schema)


def do_put_arrow_table(flight_client, table_name, arrow_table):
    upload_descriptor = flight.FlightDescriptor.for_path(table_name)
    writer, _ = flight_client.do_put(upload_descriptor, arrow_table.schema)
    writer.write(arrow_table)
    writer.close()

    # Flush the data to disk.
    action = flight.Action("FlushMemory", b"")
    results = flight_client.do_action(action)
    if results:
        print(next(results))
    else:
        print("Flushed compressed data buffers.")


# Main Function.
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"usage: {sys.argv[0]} host_address table parquet_file_or_folder [error_bound]")
        sys.exit(1)

    flight_client = flight.FlightClient(f"grpc://{sys.argv[1]}")
    table_name = sys.argv[2]
    arrow_table = read_parquet_file_or_folder(sys.argv[3])
    error_bound = sys.argv[4]

    if not table_exists(flight_client, table_name):
        create_model_table(flight_client, table_name, arrow_table.schema, error_bound)
    do_put_arrow_table(flight_client, table_name, arrow_table)