import importlib
import inspect
from pydoc import locate
import numpy as np


def param_parser(param):
    param_list = []
    if isinstance(param, list):
        for item in param:
            param_list.append(param_parser(item))

    elif isinstance(param, dict):
        param_map = {}

        if "type" in param:
            type = param.pop("type")
            name = param.pop("name")
            if type == "columntuple":
                columns = param.pop("columns")
                type_param = tuple((name, param_parser(param), columns))
            else:
                type_class = locate(type)
                type_param = type_class((name, param_parser(param)))
            return type_param

        elif "name" in param:
            name = param.pop("name")
            if name == "runtime_env":
                print()
            param_map[name] = param_parser(param)
            return param_map

        elif "ref" in param:
            return param_parser(param["ref"])

        elif "class" in param:
            if "passthrough" == param["class"]:
                return "passthrough"
            class_str = param["class"].split(".")
            module_path = param["class"].replace("." + class_str[-1], "")
            module = importlib.import_module(module_path)
            param_class = getattr(module, class_str[-1])
            param_sub_map = {}
            if "params" in param:
                param_sub_map = param_parser(param["params"])
            if "transformers" in param:
                param_sub_map["transformers"] = param_parser(param["transformers"])
                param_sub_map["remainder"] = param["remainder"]
                param_sub_map["verbose_feature_names_out"] = param[
                    "verbose_feature_names_out"
                ]

            if class_str[-1] == "ColumnTransformer":
                return (
                    param_class(**flatten_list(param_sub_map)).set_output(
                        transform="pandas"
                    )
                    if inspect.isclass(param_class)
                    else param_class
                )
            else:
                return (
                    param_class(**flatten_list(param_sub_map))
                    if inspect.isclass(param_class)
                    else param_class
                )

        elif "module" in param:
            loaded_modules = []
            for module in param["module"]:
                loaded_modules.append(importlib.import_module(module))
            return loaded_modules

        elif "func" in param:
            func_str = param["func"].split(".")
            module_path = param["func"].replace("." + func_str[-1], "")
            module = importlib.import_module(module_path)
            function = getattr(module, func_str[-1])
            return function

        elif "params" in param:
            return flatten_list(param_parser(param["params"]))

        elif "value" in param:
            return param["value"]

    return param_list


def flatten_list(param_list):
    flatten_grid = {}
    if all(isinstance(param_grid, dict) for param_grid in param_list):
        for param_grid in param_list:
            flatten_grid.update(param_grid)
        return flatten_grid
    return param_list


def arc_distance(X):
    theta_1 = X.pickup_longitude
    phi_1 = X.pickup_latitude
    theta_2 = X.dropoff_longitude
    phi_2 = X.dropoff_latitude

    temp = (
        np.sin((theta_2 - theta_1) / 2 * np.pi / 180) ** 2
        + np.cos(theta_1 * np.pi / 180)
        * np.cos(theta_2 * np.pi / 180)
        * np.sin((phi_2 - phi_1) / 2 * np.pi / 180) ** 2
    )
    distance = 2 * np.arctan2(np.sqrt(temp), np.sqrt(1 - temp))
    X["arc_distance"] = distance * 3958.8
    return X


def direction_angle(X):
    theta_1 = X.pickup_longitude
    phi_1 = X.pickup_latitude
    theta_2 = X.dropoff_longitude
    phi_2 = X.dropoff_latitude

    dtheta = theta_2 - theta_1
    dphi = phi_2 - phi_1
    radians = np.arctan2(dtheta, dphi)

    X["direction_angle"] = np.rad2deg(radians)
    return X
