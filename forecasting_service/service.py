import os

from sail.models.auto_ml.auto_pipeline import SAILAutoPipeline
from sail.pipeline import SAILPipeline

from forecasting_service.base import BaseService
from forecasting_service.parser import param_class_parser


class ForecastingService(BaseService):
    def __init__(self, modelardb_conn, message_broker, logging_level, data_dir) -> None:
        super(ForecastingService, self).__init__(
            self.__class__.__name__,
            modelardb_conn,
            message_broker,
            logging_level,
            data_dir,
        )

    def create_model_instance(self, configs):
        sail_auto_params = {}

        estimators = {}
        for estimator in configs["estimators"]:
            estimators[estimator["name"]] = param_class_parser(estimator)

        steps = []
        for step in configs["steps"]:
            steps.append((step["name"], param_class_parser(step)))

        sail_params = {}
        for sail_param in configs["sail_pipeline"]["params"]:
            sail_params[sail_param["name"]] = param_class_parser(sail_param)
        sail_auto_params["pipeline"] = SAILPipeline(steps=steps, **sail_params)

        param_grid = configs["parameter_grid"]
        estimator_ref = steps[-1][0]
        print()
        if isinstance(param_grid, list):
            for grid in param_grid:
                grid[estimator_ref] = [estimators[grid[estimator_ref][0]]]
        else:
            param_grid[estimator_ref] = [estimators[param_grid[estimator_ref][0]]]

        sail_auto_params["pipeline_params_grid"] = param_grid
        sail_auto_params["search_method"] = configs["search_method"]

        search_method_params = {}
        for sarch_param in configs["search_method_params"]:
            search_method_params[sarch_param["name"]] = param_class_parser(sarch_param)
        search_method_params["storage_path"] = os.path.join(
            self.exp_dir, "ray_results"
        )
        sail_auto_params["search_method_params"] = search_method_params

        sail_auto_params["search_data_size"] = configs["search_data_size"]
        sail_auto_params["incremental_training"] = configs["incremental_training"]
        sail_auto_params["drift_detector"] = param_class_parser(
            configs["drift_detector"]
        )
        sail_auto_params["pipeline_strategy"] = configs["pipeline_strategy"]

        return SAILAutoPipeline(**sail_auto_params)

    def process_ts_batch(self, ts_batch, model, target, timestamp_col, fit_params):
        if not super(ForecastingService, self).process_ts_batch(ts_batch, timestamp_col):
            return False

        X = ts_batch.drop([target, timestamp_col], axis=1)
        y = ts_batch[target]

        model.train(X, y, **fit_params)

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
