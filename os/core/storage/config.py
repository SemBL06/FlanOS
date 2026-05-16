from core.storage.yaml import load_yaml, save_yaml

BOOT_CONFIG_PATHS = (
    "sd/main/main.yml",
    "/sd/main/main.yml"
)

DEFAULT_CONFIG = {
    "display": {
        "main": {
            "driver": "lcd_i2c",
            "sda": 14,
            "scl": 15,
            "address": "auto",
            "rows": 4,
            "cols": 20,
            "freq": 400000
        }
    },
    "input": {},
    "output": {},
    "comm": {},
    "fetch": {
        "updates_url": ""
    },
    "wifi": {
        "SSID": "MyWifi",
        "Password": ""
    },
    "storage": {
        "sd": {
            "driver": "sd_spi",
            "slot": 0,
            "baudrate": 1000000,
            "path": "/sd",
            "sck": 18,
            "mosi": 19,
            "miso": 15,
            "cs": 17
        }
    },
    "buttons": {
        "left": 0,
        "right": 1,
        "up": 2,
        "down": 3,
        "buttons_active_low": True
    },
    "modules": {
        "enabled": True,
        "allow_override": False,
        "path": "/sd/main/modules",
        "board": "generic"
    },
    "drivers": {
        "enabled": True,
        "allow_override": False,
        "path": "/sd/main/drivers",
        "board": "generic"
    },
    "system": {
        "board": "generic"
    }
}


def get_config_path():
    i = 0
    while i < len(BOOT_CONFIG_PATHS):
        path = BOOT_CONFIG_PATHS[i]
        i += 1

        try:
            with open(path, "r"):
                return path
        except:
            pass

    return BOOT_CONFIG_PATHS[0]


def clone_value(value):
    if isinstance(value, dict):
        result = {}
        for key in value:
            result[key] = clone_value(value[key])
        return result

    if isinstance(value, list):
        result = []
        i = 0
        while i < len(value):
            result.append(clone_value(value[i]))
            i += 1
        return result

    return value


def merge_defaults(current, defaults):
    changed = False

    for key in defaults:
        default_value = defaults[key]

        if key not in current:
            current[key] = clone_value(default_value)
            changed = True
            continue

        current_value = current[key]
        if isinstance(default_value, dict) and isinstance(current_value, dict):
            if merge_defaults(current_value, default_value):
                changed = True

    return changed


def build_config(data, defaults=None):
    if defaults is None:
        defaults = DEFAULT_CONFIG

    if not isinstance(data, dict):
        data = {}

    result = clone_value(data)
    merge_defaults(result, defaults)
    return result


def load_main_config():
    return load_yaml(get_config_path())


def save_main_config(data):
    save_yaml(get_config_path(), data)


def ensure_main_config():
    return build_config(load_main_config())


def ensure_config_defaults(defaults):
    data = ensure_main_config()
    if not isinstance(defaults, dict):
        return data

    merge_defaults(data, defaults)
    return data
