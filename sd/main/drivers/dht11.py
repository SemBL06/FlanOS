try:
    import machine
except:
    machine = None

try:
    import dht as dht_lib
except:
    dht_lib = None

try:
    import time as time_lib
except:
    time_lib = None


_SENSORS = {}


def _sleep_ms(value):
    if time_lib is None:
        return
    try:
        time_lib.sleep_ms(value)
    except:
        try:
            time_lib.sleep(value / 1000)
        except:
            pass


def _to_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except:
        pass
    try:
        return int(str(value), 0)
    except:
        return default


def _normalize_pin(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip().upper()
        if text.startswith("GP"):
            return _to_int(text[2:], None)
        return _to_int(text, None)
    return _to_int(value, None)


def _get_sensor(name, config):
    sensor = _SENSORS.get(name)
    if sensor is not None:
        return sensor

    if machine is None or dht_lib is None:
        return None

    pin = _normalize_pin(config.get("pin"))
    if pin is None:
        return None

    sensor = dht_lib.DHT11(machine.Pin(pin))
    _SENSORS[name] = sensor
    return sensor


def _measure(name, config):
    sensor = _get_sensor(name, config)
    if sensor is None:
        return None

    retries = _to_int(config.get("retries"), 2)
    pause_ms = _to_int(config.get("pause_ms"), 50)
    if retries is None or retries < 1:
        retries = 1

    attempt = 0
    while attempt < retries:
        try:
            sensor.measure()
            return {
                "temperature": sensor.temperature(),
                "humidity": sensor.humidity()
            }
        except:
            _sleep_ms(pause_ms)
        attempt += 1

    return None


def get(ctx, name=None, config=None, positional=None, option=None, **kwargs):
    if not isinstance(name, str) or not name:
        ctx.log("Missing dht11 name", "ERROR")
        return None

    if not isinstance(config, dict):
        ctx.log("Invalid dht11 config for %s" % name, "ERROR")
        return None

    values = _measure(name, config)
    if not isinstance(values, dict):
        ctx.log("DHT11 read failed for %s" % name, "ERROR")
        return None

    field = option
    if field is None and isinstance(positional, list) and positional:
        field = positional[0]

    if field is None:
        return values

    field = str(field).lower()
    if field in ("temp", "temperature", "temperature_c", "c"):
        return values.get("temperature")
    if field in ("humidity", "hum", "rh"):
        return values.get("humidity")

    return values.get(field)


def get_input_provider(ctx):
    return {
        "get": get
    }


def get_manifest():
    return {
        "name": "dht11",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["input-provider", "dht11", "temperature", "humidity"]
    }
