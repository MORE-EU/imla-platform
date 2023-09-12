from sail.models.auto_ml.auto_pipeline import SAILAutoPipeline
from sail.pipeline import SAILPipeline

from forecasting_service.base import BaseService
from forecasting_service.parser import param_parser, flatten_list
from more_utils.logging import configure_logger

LOGGER = configure_logger(logger_name="ForecastingService", package_name=None)


class ForecastingService(BaseService):
    def __init__(self, modelardb_conn, message_broker, data_dir) -> None:
        super(ForecastingService, self).__init__(
            self.__class__.__name__,
            modelardb_conn,
            message_broker,
            data_dir,
        )

    def load_or_create_model(self, configs):
        if configs["model_path"]:
            model = SAILAutoPipeline.load_model(configs["model_path"])
            LOGGER.info(
                f"SAILAutoPipeline loaded successfully from - [{configs['model_path']}]."
            )
        else:
            model = self.create_model_instance(configs)
            LOGGER.info("SAILAutoPipeline created successfully.")

        return model

    def create_model_instance(self, configs):
        sail_auto_pipeline_params = {}

        sail_auto_pipeline_params["pipeline"] = SAILPipeline(
            **flatten_list(param_parser(configs["sail_pipeline"]))
        )

        sail_auto_pipeline_params["pipeline_params_grid"] = [
            flatten_list(grid) for grid in param_parser(configs["parameter_grid"])
        ]

        sail_auto_pipeline_params["search_method"] = configs["search_method"]
        sail_auto_pipeline_params["search_method_params"] = flatten_list(
            param_parser(configs["search_method_params"])
        )
        sail_auto_pipeline_params["search_method_params"]["storage_path"] = self.exp_dir
        sail_auto_pipeline_params["search_data_size"] = configs["search_data_size"]
        sail_auto_pipeline_params["incremental_training"] = configs[
            "incremental_training"
        ]
        sail_auto_pipeline_params["drift_detector"] = param_parser(
            configs["drift_detector"]
        )
        sail_auto_pipeline_params["pipeline_strategy"] = configs["pipeline_strategy"]
        sail_auto_pipeline_params["verbosity_level"] = configs["verbosity_level"]
        sail_auto_pipeline_params["verbosity_interval"] = configs["verbosity_interval"]
        sail_auto_pipeline_params["tensorboard_log_dir"] = configs[
            "tensorboard_log_dir"
        ]
        sail_auto_pipeline_params["tensorboard_log_dir"] = self.exp_dir

        return SAILAutoPipeline(**sail_auto_pipeline_params)

    def process_ts_batch(self, model, ts_batch, target, timestamp_col, fit_params):
        if not super(ForecastingService, self).process_ts_batch(
            ts_batch, timestamp_col
        ):
            return False

        time_stamps = ts_batch[timestamp_col]
        X = ts_batch.drop([target], axis=1)
        y = ts_batch[target]

        predictions = {}
        if model.best_pipeline:
            preds = model.predict(X)
            for time, pred in zip(time_stamps, preds):
                predictions[str(time)] = pred

        model.train(X, y, **fit_params)

        return predictions

    def send_response(self, json_message):
        super(ForecastingService, self).send_response(json_message)

    def log_state(self):
        super(ForecastingService, self).log_state()

    def run(self):
        super(ForecastingService, self).run()
        # self.risk_msg_thread = threading.Thread(
        #     target=self.run_forever, args=(,)
        # )
        # self.risk_msg_thread.start()
        # self.risk_msg_thread.join()
        self.run_forever(self.process_time_series)
