try:
    import machine
except:
    machine = None

try:
    import utime as time_lib
except:
    import time as time_lib


_SENSORS = {}


def _sleep_us(value):
    try:
        time_lib.sleep_us(value)
    except:
        try:
            time_lib.sleep(value / 1000000)
        except:
            pass


def _ticks_us():
    getter = getattr(time_lib, "ticks_us", None)
    if callable(getter):
        return getter()
    try:
        return int(time_lib.time() * 1000000)
    except:
        return 0


def _ticks_diff(current, start):
    diff = getattr(time_lib, "ticks_diff", None)
    if callable(diff):
        return diff(current, start)
    return current - start


def _to_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except:
        return default


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


def _make_sensor(config):
    if machine is None:
        return None

    trig_pin = _normalize_pin(config.get("trig"))
    echo_pin = _normalize_pin(config.get("echo"))

    if trig_pin is None or echo_pin is None:
        return None

    trig = machine.Pin(trig_pin, machine.Pin.OUT)
    echo = machine.Pin(echo_pin, machine.Pin.IN)
    trig.value(0)
    return {
        "trig": trig,
        "echo": echo
    }


def _get_sensor(name, config):
    sensor = _SENSORS.get(name)
    if isinstance(sensor, dict):
        return sensor

    sensor = _make_sensor(config)
    if isinstance(sensor, dict):
        _SENSORS[name] = sensor
    return sensor


def _pulse_us(sensor, timeout_us):
    pulse_func = getattr(machine, "time_pulse_us", None)
    if callable(pulse_func):
        try:
            return pulse_func(sensor["echo"], 1, timeout_us)
        except:
            return None

    start = _ticks_us()
    while sensor["echo"].value() == 0:
        if _ticks_diff(_ticks_us(), start) > timeout_us:
            return None

    pulse_start = _ticks_us()
    while sensor["echo"].value() == 1:
        if _ticks_diff(_ticks_us(), pulse_start) > timeout_us:
            return None

    return _ticks_diff(_ticks_us(), pulse_start)


def _read_distance_cm(name, config):
    if machine is None:
        return None

    sensor = _get_sensor(name, config)
    if not isinstance(sensor, dict):
        return None

    timeout_us = _to_int(config.get("timeout_us"), 30000)
    settle_us = _to_int(config.get("settle_us"), 2)
    trigger_us = _to_int(config.get("trigger_us"), 10)

    sensor["trig"].value(0)
    _sleep_us(settle_us)
    sensor["trig"].value(1)
    _sleep_us(trigger_us)
    sensor["trig"].value(0)

    pulse_us = _pulse_us(sensor, timeout_us)
    if pulse_us is None or pulse_us < 0:
        return None

    return pulse_us / 58.0


def _convert_distance(config, distance_cm, option):
    option = str(option or "cm").lower()

    if option in ("cm", "centimeter", "centimeters", "distance"):
        return distance_cm
    if option in ("mm", "millimeter", "millimeters"):
        return distance_cm * 10.0
    if option in ("meter", "meters", "m"):
        return distance_cm / 100.0
    if option in ("inch", "inches", "in"):
        return distance_cm / 2.54
    if option in ("raw", "us", "microseconds"):
        return distance_cm * 58.0
    if option in ("height", "level"):
        height_cm = _to_float(config.get("height_cm"), None)
        if height_cm is None:
            height_cm = _to_float(config.get("mount_height_cm"), None)
        if height_cm is None:
            return distance_cm
        return height_cm - distance_cm

    return distance_cm


def get(ctx, name=None, config=None, positional=None, option=None, **kwargs):
    if not isinstance(name, str) or not name:
        ctx.log("Missing ultrasonic name", "ERROR")
        return None

    if not isinstance(config, dict):
        ctx.log("Invalid ultrasonic config for %s" % name, "ERROR")
        return None

    distance_cm = _read_distance_cm(name, config)
    if distance_cm is None:
        ctx.log("Ultrasonic read failed for %s" % name, "ERROR")
        return None

    mode = option
    if mode is None and isinstance(positional, list) and positional:
        mode = positional[0]

    return _convert_distance(config, distance_cm, mode)


def get_input_provider(ctx):
    return {
        "get": get
    }


def get_manifest():
    return {
        "name": "ultrasonic",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["input-provider", "ultrasonic", "distance"]
    }
