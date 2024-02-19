from sail.models.auto_ml.auto_pipeline import SAILAutoPipeline
from sail.pipeline import SAILPipeline
import os
from imla_platform.base import BaseService
from imla_platform.parser import param_parser, flatten_list
from more_utils.logging import configure_logger

LOGGER = configure_logger(logger_name="IMLAPlatform", package_name=None)


class IMLAPlatform(BaseService):
    def __init__(self, modelardb_conn, message_broker, data_dir) -> None:
        super(IMLAPlatform, self).__init__(
            self.__class__.__name__,
            modelardb_conn,
            message_broker,
            data_dir,
        )

    def load_or_create_model(self, configs, tracer):
        if configs["model_path"]:
            model = SAILAutoPipeline.load_model(configs["model_path"])
            LOGGER.info(
                f"SAILAutoPipeline loaded successfully from - [{configs['model_path']}]."
            )
            model.pipeline_strategy.tracer = tracer
        else:
            model = self.create_model_instance(configs, tracer)
            LOGGER.info("SAILAutoPipeline created successfully.")

        return model

    def create_model_instance(self, configs, tracer):
        sail_auto_pipeline_params = {}

        try:
            sail_auto_pipeline_params["pipeline"] = SAILPipeline(
                **flatten_list(param_parser(configs["sail_pipeline"]))
            )

            if isinstance(configs["parameter_grid"], list):
                sail_auto_pipeline_params["pipeline_params_grid"] = [
                    flatten_list(grid) for grid in param_parser(configs["parameter_grid"])
                ]
            else:
                sail_auto_pipeline_params["pipeline_params_grid"] = flatten_list(
                    param_parser(configs["parameter_grid"])[0]
                )

            sail_auto_pipeline_params["search_method"] = configs["search_method"]
            sail_auto_pipeline_params["search_method_params"] = flatten_list(
                param_parser(configs["search_method_params"])
            )

            if os.environ.get("POD_NAME"):
                exp_dir = self.exp_dir.split("/")[-1]
                data_dir = self.exp_dir.replace(exp_dir, "")
                storage_path = os.path.join(data_dir, os.environ.get("POD_NAME"), exp_dir)
            else:
                storage_path = self.exp_dir

            sail_auto_pipeline_params["search_method_params"]["storage_path"] = storage_path
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

            if configs["tensorboard_log_dir"]:
                sail_auto_pipeline_params["tensorboard_log_dir"] = self.exp_dir

            sail_auto_pipeline_params["tracer"] = tracer

            return SAILAutoPipeline(**sail_auto_pipeline_params)
        
        except Exception as e:
            LOGGER.error(f"Error in parsing configs: {str(e)}")
            raise Exception(f"Error in parsing configs: {str(e)}")

    def process_ts_batch(self, model, ts_batch, target, timestamp_col, fit_params):
        if not super(IMLAPlatform, self).process_ts_batch(
            ts_batch, timestamp_col
        ):
            return False

        if timestamp_col:
            indexes = ts_batch[timestamp_col]
        else:
            indexes = range(len(ts_batch))

        X = ts_batch.drop([target], axis=1)
        y = ts_batch[target]

        predictions = {}
        if model.best_pipeline:
            preds = model.predict(X)
            for index, pred in zip(indexes, preds):
                try:
                    predictions[str(int(index.timestamp()))] = pred
                except:
                    predictions[str(index)] = pred

        try:
            model.train(X, y, **fit_params)
        except Exception as e:
            raise Exception(f"ERROR in SAIL: {str(e)}")

        return predictions

    def send_response(self, json_message):
        super(IMLAPlatform, self).send_response(json_message)

    def log_state(self):
        super(IMLAPlatform, self).log_state()

    def run(self):
        super(IMLAPlatform, self).run()
        self.run_forever(self.process_time_series)
