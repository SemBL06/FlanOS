try:
    import machine
except:
    machine = None


CONFIG_DEFAULTS = {
    "display": {
        "main": {
            "driver": "lcd_i2c",
            "sda": 0,
            "scl": 1,
            "address": "auto",
            "rows": 4,
            "cols": 20,
            "freq": 400000
        }
    }
}


_STATE = {
    "lcd": None,
    "mode": "offline",
    "config": {},
    "entry": None,
    "cursor_x": 0,
    "cursor_y": 0,
    "backlight": "on"
}


def _to_int(value, default):
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


def _pick_arg(positional, index, fallback=None, default=None):
    if positional is not None and len(positional) > index:
        return positional[index]
    if fallback is not None:
        return fallback
    return default


def _load_driver():
    from _i2c_lcd import I2cLcd
    return I2cLcd


def _get_config_module(ctx):
    executor = getattr(ctx, "executor", None)
    if executor is None:
        return None
    module = executor.modules.get("config")
    if isinstance(module, dict):
        return module
    return None


def _config_get(ctx, key, default=None):
    module = _get_config_module(ctx)
    if module is None:
        return default
    getter = module.get("get")
    if not callable(getter):
        return default
    value = getter(ctx, key)
    if value is None:
        return default
    return value


def _config_prefix(ctx):
    if _STATE.get("entry"):
        return "display." + _STATE["entry"]
    return "display.main"


def _config_save(ctx, key, value):
    module = _get_config_module(ctx)
    if module is None:
        return value
    saver = module.get("save")
    if not callable(saver):
        return value
    return saver(ctx, key, value)


def _read_config(ctx):
    entry = _get_selected_entry(ctx)
    if entry is None:
        return {
            "enabled": False,
            "sda": 0,
            "scl": 1,
            "address": "auto",
            "rows": 4,
            "cols": 20,
            "freq": 400000
        }

    return {
        "enabled": bool(entry.get("enabled", True)),
        "sda": _to_int(entry.get("sda", 0), 0),
        "scl": _to_int(entry.get("scl", 1), 1),
        "address": entry.get("address", "auto"),
        "rows": _to_int(entry.get("rows", 4), 4),
        "cols": _to_int(entry.get("cols", 20), 20),
        "freq": _to_int(entry.get("freq", 400000), 400000)
    }


def _get_display_entries(ctx):
    display = _config_get(ctx, "display", {})
    if not isinstance(display, dict):
        return []

    entries = []
    for name in display:
        entry = display.get(name)
        if not isinstance(entry, dict):
            continue
        if str(entry.get("driver", "")).lower() == "lcd_i2c":
            item = {}
            for key in entry:
                item[key] = entry[key]
            item["_name"] = name
            entries.append(item)
    return entries


def _get_selected_entry(ctx):
    entries = _get_display_entries(ctx)
    if not entries:
        return None

    wanted = _STATE.get("entry")
    if wanted:
        i = 0
        while i < len(entries):
            if entries[i].get("_name") == wanted:
                return entries[i]
            i += 1

    return entries[0]


def _normalize_address(value):
    if value in (None, "", "auto"):
        return None
    return _to_int(value, 39)


def _format_address(value):
    return "0x%02x" % int(value)


def _discover_address(settings):
    if machine is None:
        return None

    try:
        bus = machine.I2C(
            0,
            sda=machine.Pin(settings["sda"]),
            scl=machine.Pin(settings["scl"]),
            freq=settings["freq"]
        )
        devices = bus.scan()
        if devices:
            return devices[0]
    except:
        pass

    return None


def probe(ctx):
    entries = _get_display_entries(ctx)
    if not entries:
        _STATE["entry"] = None
        _STATE["mode"] = "offline"
        return False

    i = 0
    while i < len(entries):
        settings = entries[i]
        if not settings.get("enabled", True):
            i += 1
            continue

        if machine is None:
            _STATE["entry"] = settings.get("_name")
            _STATE["config"] = _read_config(ctx)
            _STATE["mode"] = "mock"
            return True

        address = _normalize_address(settings.get("address"))
        if address is None:
            address = _discover_address(settings)
        else:
            try:
                bus = machine.I2C(
                    0,
                    sda=machine.Pin(_to_int(settings.get("sda", 0), 0)),
                    scl=machine.Pin(_to_int(settings.get("scl", 1), 1)),
                    freq=_to_int(settings.get("freq", 400000), 400000)
                )
                if address not in bus.scan():
                    address = None
            except:
                address = None

        if address is not None:
            _STATE["entry"] = settings.get("_name")
            settings["address"] = _format_address(address)
            _STATE["config"] = _read_config(ctx)
            return True
        i += 1

    _STATE["entry"] = None
    _STATE["mode"] = "offline"
    return False


def autoconfigure(ctx, config):
    if not isinstance(config, dict):
        return config

    prefix = "lcd_i2c"
    settings = config.get("lcd_i2c", {})
    display = config.get("display", {})
    if isinstance(display, dict):
        display_main = display.get("main", {})
        if isinstance(display_main, dict):
            driver = str(display_main.get("driver", "lcd_i2c")).lower()
            if driver == "lcd_i2c":
                prefix = "display.main"
                settings = display_main
    if not isinstance(settings, dict):
        settings = {}
        if prefix == "display.main":
            if not isinstance(display, dict):
                display = {}
                config["display"] = display
            display["main"] = settings
        else:
            config["lcd_i2c"] = settings

    current = settings.get("address", "auto")
    if current not in (None, "", "auto"):
        return config

    if machine is None:
        return config

    detected = _discover_address({
        "sda": _to_int(settings.get("sda", 0), 0),
        "scl": _to_int(settings.get("scl", 1), 1),
        "freq": _to_int(settings.get("freq", 400000), 400000)
    })
    if detected is not None:
        settings["address"] = _format_address(detected)
        ctx.log("Auto-detected %s address %s" % (prefix, settings["address"]))

    return config


def _ensure_lcd(ctx):
    if _STATE["lcd"] is not None:
        return _STATE["lcd"]

    if not probe(ctx):
        _STATE["lcd"] = None
        return None

    settings = _read_config(ctx)
    _STATE["config"] = settings

    if not settings.get("enabled", True):
        _STATE["lcd"] = None
        _STATE["mode"] = "disabled"
        return None

    if machine is None:
        _STATE["lcd"] = None
        _STATE["mode"] = "mock"
        return None

    address = _normalize_address(settings.get("address"))
    if address is None:
        address = _discover_address(settings)
        if address is not None:
            settings["address"] = _format_address(address)
            _config_save(ctx, _config_prefix(ctx) + ".address", settings["address"])
            _STATE["config"] = settings

    if address is None:
        _STATE["mode"] = "offline"
        return None

    I2cLcd = _load_driver()
    i2c = machine.I2C(
        0,
        sda=machine.Pin(settings["sda"]),
        scl=machine.Pin(settings["scl"]),
        freq=settings["freq"]
    )
    _STATE["lcd"] = I2cLcd(i2c, address, settings["rows"], settings["cols"])
    _STATE["mode"] = "ready"
    return _STATE["lcd"]


def _write_text(ctx, text, x, y):
    lcd = _ensure_lcd(ctx)
    if lcd is None:
        return text

    lcd.move_to(int(x), int(y))
    lcd.putstr(str(text))
    _STATE["cursor_x"] = int(x)
    _STATE["cursor_y"] = int(y)
    return text


def display_line(ctx, payload):
    if not isinstance(payload, list):
        return payload

    i = 0
    while i < len(payload):
        item = payload[i]
        if isinstance(item, dict):
            _write_text(ctx, item.get("text", ""), item.get("x", 0), item.get("y", i))
        i += 1

    return payload


def display_clear(ctx, payload=None):
    lcd = _ensure_lcd(ctx)
    if lcd is not None:
        lcd.clear()
    _STATE["cursor_x"] = 0
    _STATE["cursor_y"] = 0
    return True


def display_invert(ctx, payload=None):
    return False


def display_shapes(ctx, payload):
    if not isinstance(payload, dict):
        return payload

    text = payload.get("text", "")
    return _write_text(ctx, text, payload.get("x", 0), payload.get("y", 0))


def display_image(ctx, payload):
    return payload


def get(ctx, *positional, field=None):
    field = _pick_arg(positional, 0, field)
    _STATE["config"] = _read_config(ctx)
    data = {
        "status": _STATE["mode"],
        "sda": _STATE["config"].get("sda", 0),
        "scl": _STATE["config"].get("scl", 1),
        "address": _STATE["config"].get("address", "auto"),
        "rows": _STATE["config"].get("rows", 4),
        "cols": _STATE["config"].get("cols", 20),
        "provider": "display"
    }
    if field:
        return data.get(str(field).lower())
    return data


def get_module():
    return {
        "get": get
    }


def get_display_provider(ctx):
    settings = _read_config(ctx)
    return {
        "width": settings.get("cols", 20),
        "height": settings.get("rows", 4),
        "probe": probe,
        "line": display_line,
        "clear": display_clear,
        "invert": display_invert,
        "shapes": display_shapes,
        "image": display_image
    }


def get_config_defaults():
    return CONFIG_DEFAULTS


def get_manifest():
    return {
        "name": "lcd_i2c",
        "version": "2.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": ["config"],
        "capabilities": ["display-provider", "i2c", "lcd"]
    }
