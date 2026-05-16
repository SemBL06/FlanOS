try:
    import machine
except:
    machine = None


CONFIG_DEFAULTS = {
    "display": {
        "main": {
            "driver": "oled",
            "sda": 4,
            "scl": 5,
            "address": "auto",
            "width": 128,
            "height": 64,
            "freq": 100000
        }
    }
}


_STATE = {
    "display": None,
    "mode": "offline",
    "config": {},
    "entry": None
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


def _chars_for_width(width):
    return max(1, int(width) // 8)


def _rows_for_height(height):
    return max(1, int(height) // 8)


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


def _read_config(ctx):
    current = _STATE.get("config")
    if isinstance(current, dict) and current.get("entry") == _STATE.get("entry"):
        return current

    entry = _get_selected_entry(ctx)
    if entry is None:
        return {
            "enabled": False,
            "sda": 4,
            "scl": 5,
            "address": 0x3C,
            "width": 128,
            "height": 64,
            "freq": 400000
        }

    return {
        "enabled": bool(entry.get("enabled", True)),
        "sda": _to_int(entry.get("sda", 4), 4),
        "scl": _to_int(entry.get("scl", 5), 5),
        "address": _parse_address(entry.get("address", "auto"), 0x3C),
        "width": _to_int(entry.get("width", 128), 128),
        "height": _to_int(entry.get("height", 64), 64),
        "freq": _to_int(entry.get("freq", 100000), 100000)
    }


def _parse_address(value, default):
    if value in (None, "", "auto"):
        return None
    return _to_int(value, default)


def _get_display_entries(ctx):
    display = _config_get(ctx, "display", {})
    if not isinstance(display, dict):
        return []

    entries = []
    for name in display:
        entry = display.get(name)
        if not isinstance(entry, dict):
            continue
        if str(entry.get("driver", "")).lower() == "oled":
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


def _load_lib():
    try:
        import _ssd1306 as ssd1306
        return ssd1306
    except:
        return None


def _candidate_freqs(settings):
    primary = _to_int(settings.get("freq", 100000), 100000)
    values = [primary, 100000]
    result = []
    i = 0
    while i < len(values):
        value = values[i]
        i += 1
        if value not in result:
            result.append(value)
    return result


def _candidate_sizes(settings):
    width = _to_int(settings.get("width", 128), 128)
    height = _to_int(settings.get("height", 64), 64)
    values = [
        (width, height),
        (128, 64),
        (128, 32)
    ]
    result = []
    i = 0
    while i < len(values):
        value = values[i]
        i += 1
        if value not in result:
            result.append(value)
    return result


def _format_addresses(addresses):
    if not isinstance(addresses, list) or not addresses:
        return "none"

    parts = []
    i = 0
    while i < len(addresses):
        parts.append("0x%02X" % int(addresses[i]))
        i += 1
    return ", ".join(parts)


def _create_i2c(settings, freq):
    return machine.I2C(
        0,
        sda=machine.Pin(_to_int(settings.get("sda", 4), 4)),
        scl=machine.Pin(_to_int(settings.get("scl", 5), 5)),
        freq=freq
    )


def _create_soft_i2c(settings, freq):
    soft = getattr(machine, "SoftI2C", None)
    if soft is None:
        return None
    return soft(
        sda=machine.Pin(_to_int(settings.get("sda", 4), 4)),
        scl=machine.Pin(_to_int(settings.get("scl", 5), 5)),
        freq=freq
    )


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

        try:
            configured_address = _parse_address(settings.get("address", "auto"), 0x3C)
            freqs = _candidate_freqs(settings)
            j = 0
            while j < len(freqs):
                freq = freqs[j]
                j += 1
                i2c = _create_i2c(settings, freq)
                addresses = i2c.scan()
                if configured_address is None:
                    if not addresses:
                        continue
                    address = addresses[0]
                else:
                    address = configured_address
                    if address not in addresses:
                        continue

                ctx.log(
                    "OLED scan on GP%s/GP%s @ %sHz found: %s" % (
                        _to_int(settings.get("sda", 4), 4),
                        _to_int(settings.get("scl", 5), 5),
                        freq,
                        _format_addresses(addresses)
                    )
                )

                _STATE["entry"] = settings.get("_name")
                _STATE["display"] = None
                _STATE["config"] = {
                    "entry": settings.get("_name"),
                    "enabled": bool(settings.get("enabled", True)),
                    "sda": _to_int(settings.get("sda", 4), 4),
                    "scl": _to_int(settings.get("scl", 5), 5),
                    "address": address,
                    "width": _to_int(settings.get("width", 128), 128),
                    "height": _to_int(settings.get("height", 64), 64),
                    "freq": freq
                }
                _STATE["mode"] = "found"
                return True
        except Exception as e:
            _STATE["display"] = None
            _STATE["mode"] = "offline"
            ctx.log("OLED probe failed for %s: %s" % (settings.get("_name", "oled"), e), "WARN")
        i += 1

    _STATE["entry"] = None
    _STATE["mode"] = "offline"
    return False


def _ensure_display(ctx):
    if _STATE["display"] is not None:
        return _STATE["display"]

    if not probe(ctx):
        _STATE["display"] = None
        return None

    settings = _STATE.get("config")
    if not isinstance(settings, dict):
        settings = _read_config(ctx)
        _STATE["config"] = settings

    if not settings.get("enabled", True):
        _STATE["display"] = None
        _STATE["mode"] = "disabled"
        return None

    if machine is None:
        _STATE["display"] = None
        _STATE["mode"] = "mock"
        return None

    ssd1306 = _load_lib()
    if ssd1306 is None:
        _STATE["mode"] = "missing_lib"
        return None

    sizes = _candidate_sizes(settings)
    freqs = _candidate_freqs(settings)
    freq_index = 0
    while freq_index < len(freqs):
        freq = freqs[freq_index]
        freq_index += 1
        variants = [
            ("i2c", _create_i2c(settings, freq)),
            ("soft", _create_soft_i2c(settings, freq))
        ]

        variant_index = 0
        while variant_index < len(variants):
            variant_name, i2c = variants[variant_index]
            variant_index += 1
            if i2c is None:
                continue

            size_index = 0
            while size_index < len(sizes):
                width, height = sizes[size_index]
                size_index += 1
                try:
                    display = ssd1306.SSD1306_I2C(
                        width,
                        height,
                        i2c,
                        addr=settings["address"]
                    )
                    display.fill(0)
                    display.show()
                    _STATE["display"] = display
                    _STATE["config"]["entry"] = _STATE.get("entry")
                    _STATE["config"]["width"] = width
                    _STATE["config"]["height"] = height
                    _STATE["config"]["freq"] = freq
                    _STATE["mode"] = "ready"
                    if variant_name == "soft":
                        ctx.log("OLED using SoftI2C fallback", "WARN")
                    if width != settings["width"] or height != settings["height"]:
                        ctx.log("OLED fallback geometry selected: %sx%s" % (width, height), "WARN")
                    return _STATE["display"]
                except Exception as e:
                    ctx.log("OLED init failed at %sx%s via %s: %s" % (width, height, variant_name, e), "WARN")

    _STATE["display"] = None
    _STATE["mode"] = "offline"
    return None


def available(ctx):
    return _ensure_display(ctx) is not None


def display_line(ctx, payload):
    try:
        oled = _ensure_display(ctx)
    except Exception as e:
        _STATE["display"] = None
        _STATE["mode"] = "offline"
        ctx.log("OLED line failed: %s" % e, "WARN")
        return payload
    if oled is None:
        return payload

    try:
        if isinstance(payload, list):
            i = 0
            while i < len(payload):
                item = payload[i]
                if isinstance(item, dict):
                    row = int(item.get("y", 0)) * 8
                    try:
                        oled.fill_rect(0, row, int(_STATE["config"].get("width", 128)), 8, 0)
                    except:
                        pass
                    oled.text(
                        str(item.get("text", "")),
                        int(item.get("x", 0)) * 8,
                        row
                    )
                i += 1
        oled.show()
    except Exception as e:
        _STATE["display"] = None
        _STATE["mode"] = "offline"
        ctx.log("OLED draw failed: %s" % e, "WARN")
    return payload


def display_clear(ctx, payload=None):
    try:
        oled = _ensure_display(ctx)
    except Exception as e:
        _STATE["display"] = None
        _STATE["mode"] = "offline"
        ctx.log("OLED clear failed: %s" % e, "WARN")
        return True
    if oled is not None:
        try:
            oled.fill(0)
            oled.show()
        except Exception as e:
            _STATE["display"] = None
            _STATE["mode"] = "offline"
            ctx.log("OLED clear failed: %s" % e, "WARN")
    return True


def display_invert(ctx, payload=None):
    try:
        oled = _ensure_display(ctx)
    except Exception as e:
        _STATE["display"] = None
        _STATE["mode"] = "offline"
        ctx.log("OLED invert failed: %s" % e, "WARN")
        return False
    if oled is None:
        return False

    state = bool(payload.get("inverted", False)) if isinstance(payload, dict) else False
    try:
        oled.invert(1 if state else 0)
        oled.show()
        return state
    except Exception as e:
        _STATE["display"] = None
        _STATE["mode"] = "offline"
        ctx.log("OLED invert failed: %s" % e, "WARN")
        return False


def display_shapes(ctx, payload):
    if not isinstance(payload, dict):
        return payload
    return display_line(ctx, [payload])


def display_image(ctx, payload):
    return payload


def get(ctx, *positional, field=None):
    if positional:
        field = positional[0]

    settings = _read_config(ctx)
    data = {
        "status": _STATE.get("mode", "offline"),
        "width": settings.get("width", 128),
        "height": settings.get("height", 64),
        "cols": _chars_for_width(settings.get("width", 128)),
        "rows": _rows_for_height(settings.get("height", 64)),
        "address": settings.get("address", 0x3C),
        "provider": "display"
    }

    if field:
        return data.get(str(field).lower())
    return data


def get_display_provider(ctx):
    settings = _read_config(ctx)
    return {
        "width": _chars_for_width(settings.get("width", 128)),
        "height": _rows_for_height(settings.get("height", 64)),
        "available": available,
        "probe": probe,
        "line": display_line,
        "clear": display_clear,
        "invert": display_invert,
        "shapes": display_shapes,
        "image": display_image
    }


def get_module():
    return {
        "get": get
    }


def get_config_defaults():
    return CONFIG_DEFAULTS


def get_manifest():
    return {
        "name": "oled",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": ["config"],
        "capabilities": ["display-provider", "oled", "ssd1306", "i2c"]
    }
