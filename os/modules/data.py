from core.storage.config import ensure_main_config, get_config_path, save_main_config
from core.storage.yaml import load_yaml, save_yaml
from core.utils.paths import get_path_value, set_path_value


def get_script_data_path(ctx):
    return ctx.data_path + "/data.yml"


def normalize_file_alias(ctx, file=None):
    if file is None:
        return get_config_path()

    if not isinstance(file, str):
        file = str(file)

    lowered = file.lower()
    if lowered in ("main", "config"):
        return get_config_path()
    if lowered in ("data", "script"):
        return get_script_data_path(ctx)

    if file.startswith("/"):
        return file

    if file.endswith(".yml") or file.endswith(".yaml"):
        return ctx.data_path + "/" + file

    return file


def load_data_file(ctx, file=None):
    path = normalize_file_alias(ctx, file)
    if path == get_config_path():
        return path, ensure_main_config()
    return path, load_yaml(path)


def save_data_file(path, data):
    if path == get_config_path():
        save_main_config(data)
    else:
        save_yaml(path, data)


def normalize_path_arg(positional, path=None, file=None):
    if path is not None:
        return file, path

    if len(positional) >= 2:
        return positional[0], positional[1]

    if len(positional) == 1:
        return file, positional[0]

    return file, path


def require_path(ctx, path):
    if isinstance(path, str) and path:
        return True

    ctx.log("Data path is required", "ERROR")
    return False


def data_get(ctx, *positional, file=None, path=None):
    file, path = normalize_path_arg(positional, path=path, file=file)
    if not require_path(ctx, path):
        return None

    _, data = load_data_file(ctx, file=file)
    return get_path_value(data, path)


def data_save(ctx, *positional, file=None, path=None, value=None):
    file, path = normalize_path_arg(positional, path=path, file=file)
    if value is None and len(positional) > 2:
        value = positional[2]
    if not require_path(ctx, path):
        return None

    data_path, data = load_data_file(ctx, file=file)
    resolved = ctx.executor.resolve(value)
    set_path_value(data, path, resolved)
    save_data_file(data_path, data)
    ctx.log("Saved %s to %s" % (path, data_path))
    return resolved


def data_append(ctx, *positional, file=None, path=None, value=None):
    file, path = normalize_path_arg(positional, path=path, file=file)
    if value is None and len(positional) > 2:
        value = positional[2]
    if not require_path(ctx, path):
        return None

    data_path, data = load_data_file(ctx, file=file)
    current = get_path_value(data, path)
    if current is None:
        current = []
    if not isinstance(current, list):
        current = [current]

    current.append(ctx.executor.resolve(value))
    set_path_value(data, path, current)
    save_data_file(data_path, data)
    ctx.log("Appended %s to %s" % (path, data_path))
    return current


def get_module():
    return {
        "get": data_get,
        "save": data_save,
        "append": data_append
    }
