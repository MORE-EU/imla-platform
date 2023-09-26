from more_utils.logging import configure_logger
from time import sleep
import pandas as pd
import pathlib
from pyarrow.parquet import ParquetFile
import pyarrow


LOGGER = configure_logger(logger_name="DataStream", package_name=None)


class DataStream:
    def __init__(self, data_stream) -> None:
        self.data_configs = data_stream

    def get_training_params(self, final_estimator_name):
        fit_params = {}
        if len(self.data_configs["classes"]) > 0:
            fit_params[f"{final_estimator_name}__classes"] = self.data_configs[
                "classes"
            ]

        target = self.data_configs["target"]
        timestamp_col = self.data_configs["timestamp_col"]

        return target, timestamp_col, fit_params

    def validate_batch(self, ts_batch):
        if ts_batch.shape[0] <= 0:
            LOGGER.error(
                f"Empty Time-series batch received. Ignoring bad time-series batch."
            )
            return False
        elif list(ts_batch.columns) != self.features_:
            LOGGER.error(
                f"Missing features in a current batch: {list(set(self.features_).intersection(set(ts_batch.columns)))}. Ignoring bad time-series batch."
            )
            return False

        return True

    def wait(self):
        sleep(self.data_configs["data_ingestion_freq"])


class ModelarDBDataStream(DataStream):
    def __init__(self, data_stream, ts_factory) -> None:
        super(ModelarDBDataStream, self).__init__(data_stream)
        self.ts_factory = ts_factory

    def get_data_session(self):
        time_series = self.ts_factory.create_time_series(
            model_table=self.data_configs["model_table_or_path"],
            from_date=self.data_configs["from_date"],
            to_date=self.data_configs["to_date"],
            limit=self.data_configs["data_limit"],
        )

        features = list(time_series.columns)
        target = self.data_configs["target"]
        data_session = time_series.fetch_next(
            batch_size=self.data_configs["data_batch_size"]
        )
        LOGGER.info(
            f"Data session created. Time-series found with features: {list(set(features) - set([target]))} and target: {target}"
        )
        self.features_ = features

        return data_session


class LocalDataStream(DataStream):
    def __init__(self, data_stream, *args, **kwargs) -> None:
        super(LocalDataStream, self).__init__(data_stream)

    def get_data_session(self):
        file_path = self.data_configs["model_table_or_path"]
        extension = pathlib.Path(file_path).suffix
        if ".csv" == extension.lower():
            time_series_df = pd.read_csv(
                file_path,
                usecols=self.data_configs["selected_features"],
                nrows=self.data_configs["data_limit"],
                chunksize=self.data_configs["data_batch_size"],
            )
            # reading again a single row to get feature names
            features = list(
                pd.read_csv(
                    file_path,
                    nrows=1,
                ).columns
            )
        elif ".parquet" == extension.lower():
            parquet_file = ParquetFile(file_path)
            features = parquet_file.schema.names
            time_series_df = self.iter_parquet_file(
                parquet_file,
                self.data_configs["data_batch_size"],
                self.data_configs["data_limit"],
                self.data_configs["selected_features"],
            )
        else:
            raise Exception(
                f"Invalid local file path for the data stream: {file_path}. Only files with the extension as .parquet and .csv are accepted."
            )

        target = self.data_configs["target"]
        data_session = time_series_df

        LOGGER.info(
            f"Data session created. Time-series found with features: {list(set(features) - set([target]))} and target: {target}"
        )
        self.features_ = features

        return data_session

    def iter_parquet_file(
        self, parquet_file, batch_size, total_rows=None, selected_features=None
    ):
        n_rows = 0
        batch_gen = parquet_file.iter_batches(
            columns=selected_features,
            use_threads=True,
            batch_size=batch_size,
        )

        def check_loop_condition(n_rows, total_rows):
            if total_rows:
                return n_rows < total_rows
            else:
                return True

        while check_loop_condition(n_rows, total_rows):
            yield pyarrow.Table.from_batches([next(batch_gen)]).to_pandas()
            n_rows += batch_size


class DataStreamFactory:
    @classmethod
    def create_data_stream(cls, data_stream, *args, **kwargs):
        if "modelardb" == data_stream["source"]:
            return ModelarDBDataStream(data_stream, *args, **kwargs)
        elif "local_file" == data_stream["source"]:
            return LocalDataStream(data_stream, *args, **kwargs)
        else:
            raise Exception(
                f"Invalid data stream source type: {data_stream['source']}. Source can only have one of the two values: [modelardb, local_file]"
            )
