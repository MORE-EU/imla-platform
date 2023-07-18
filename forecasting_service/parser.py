import importlib
import inspect


def param_class_parser(param: dict):
    if "class" in param:
        class_str = param["class"].split(".")
        module_path = param["class"].replace("." + class_str[-1], "")
        module = importlib.import_module(module_path)
        param_class = getattr(module, class_str[-1])
        param_map = {}
        if "params" in param:
            for sub_param in param["params"]:
                if "class" in sub_param:
                    param_map[sub_param["name"]] = param_class_parser(sub_param)
                else:
                    param_map[sub_param["name"]] = sub_param["value"]
        return param_class(**param_map) if inspect.isclass(param_class) else param_class
    return param["value"]
