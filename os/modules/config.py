import modules.data as data_module
from core.utils.args import pick_arg


def get(ctx, *positional, id=None, path=None):
    path = pick_arg(positional, 0, path if path is not None else id)
    return data_module.data_get(ctx, file="main", path=path)


def save(ctx, *positional, id=None, path=None, value=None):
    path = pick_arg(positional, 0, path if path is not None else id)
    value = pick_arg(positional, 1, value)
    return data_module.data_save(ctx, file="main", path=path, value=value)


def get_module():
    return {
        "get": get,
        "save": save
    }
