try:
    import machine
except:
    machine = None


_READERS = {}


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


def _load_lib():
    try:
        from pn532 import PN532_I2C
        return PN532_I2C
    except:
        pass

    try:
        from pn532_i2c import PN532_I2C
        return PN532_I2C
    except:
        return None


def _get_reader(name, config):
    reader = _READERS.get(name)
    if reader is not None:
        return reader

    if machine is None:
        return None

    PN532_I2C = _load_lib()
    if PN532_I2C is None:
        return None

    sda = _normalize_pin(config.get("sda"))
    scl = _normalize_pin(config.get("scl"))
    if sda is None or scl is None:
        return None

    i2c = machine.I2C(
        0,
        sda=machine.Pin(sda),
        scl=machine.Pin(scl),
        freq=_to_int(config.get("freq"), 400000)
    )
    reader = PN532_I2C(i2c, debug=False)
    if hasattr(reader, "SAM_configuration"):
        try:
            reader.SAM_configuration()
        except:
            pass
    _READERS[name] = reader
    return reader


def _read_uid(name, config):
    reader = _get_reader(name, config)
    if reader is None:
        return None

    if hasattr(reader, "read_passive_target"):
        try:
            uid = reader.read_passive_target(timeout=0.5)
            if uid:
                return uid
        except:
            pass

    if hasattr(reader, "read_passive_target"):
        try:
            uid = reader.read_passive_target()
            if uid:
                return uid
        except:
            pass

    return None


def _format_uid(uid):
    if uid is None:
        return None

    try:
        parts = []
        i = 0
        while i < len(uid):
            parts.append("%02X" % uid[i])
            i += 1
        return ":".join(parts)
    except:
        return str(uid)


def get(ctx, name=None, config=None, positional=None, option=None, **kwargs):
    if not isinstance(name, str) or not name:
        ctx.log("Missing pn532 name", "ERROR")
        return None

    if not isinstance(config, dict):
        ctx.log("Invalid pn532 config for %s" % name, "ERROR")
        return None

    field = option
    if field is None and isinstance(positional, list) and positional:
        field = positional[0]
    if field is None:
        field = "uid"

    uid = _read_uid(name, config)
    field = str(field).lower()

    if field in ("present", "detected"):
        return uid is not None
    if field in ("uid", "tag", "card"):
        return _format_uid(uid)

    return None


def get_input_provider(ctx):
    return {
        "get": get
    }


def get_manifest():
    return {
        "name": "pn532",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["input-provider", "nfc", "rfid", "pn532", "i2c"]
    }
