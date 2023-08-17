import importlib
import inspect
from pydoc import locate


def param_parser(param):
    param_list = []
    if isinstance(param, list):
        for item in param:
            param_list.append(param_parser(item))

    elif isinstance(param, dict):
        param_map = {}

        if "type" in param:
            type = locate(param.pop("type"))
            name = param.pop("name")
            type_param = type((name, param_parser(param)))
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
            class_str = param["class"].split(".")
            module_path = param["class"].replace("." + class_str[-1], "")
            module = importlib.import_module(module_path)
            param_class = getattr(module, class_str[-1])
            param_sub_map = {}
            if "params" in param:
                param_sub_map = param_parser(param["params"])
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
