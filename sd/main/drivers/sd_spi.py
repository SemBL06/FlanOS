try:
    import machine
except:
    machine = None

try:
    import uos as os_lib
except:
    import os as os_lib

try:
    from core.storage.sdcard import SDCard, normalize_pin, normalize_mount_path, to_int
except:
    SDCard = None


_STATE = {
    "mounted": False,
    "path": None,
    "card": None
}


def _mount_path(path):
    return normalize_mount_path(path or "/sd")


def _load_lib():
    return SDCard


def mount(ctx, *positional, sck=None, mosi=None, miso=None, cs=None, slot=0, baudrate=1000000, path="/sd"):
    if machine is None:
        ctx.log("SD SPI unavailable", "ERROR")
        return "offline"

    SDCard = _load_lib()
    if SDCard is None:
        ctx.log("SD card library unavailable", "ERROR")
        return "offline"

    if positional:
        path = positional[0]

    sck_pin = normalize_pin(sck)
    mosi_pin = normalize_pin(mosi)
    miso_pin = normalize_pin(miso)
    cs_pin = normalize_pin(cs)

    if None in (sck_pin, mosi_pin, miso_pin, cs_pin):
        ctx.log("Missing SD SPI pins", "ERROR")
        return "offline"

    target = _mount_path(path)
    try:
        os_lib.listdir(target)
        _STATE["mounted"] = True
        _STATE["path"] = target
        return target
    except:
        pass

    try:
        spi = machine.SPI(
            int(slot),
            baudrate=to_int(baudrate, 1000000),
            polarity=0,
            phase=0,
            sck=machine.Pin(sck_pin),
            mosi=machine.Pin(mosi_pin),
            miso=machine.Pin(miso_pin)
        )
        card = SDCard(spi, machine.Pin(cs_pin, machine.Pin.OUT))
        vfs = os_lib.VfsFat(card)
        os_lib.mount(vfs, target)
        _STATE["mounted"] = True
        _STATE["path"] = target
        _STATE["card"] = card
        return target
    except Exception as e:
        ctx.log("SD mount failed: %s" % e, "ERROR")
        return "offline"


def unmount(ctx, *positional, path=None):
    if positional:
        path = positional[0]

    target = _mount_path(path or _STATE.get("path") or "/sd")
    try:
        os_lib.umount(target)
    except:
        pass

    _STATE["mounted"] = False
    _STATE["path"] = None
    _STATE["card"] = None
    return True


def status(ctx):
    if _STATE.get("mounted"):
        return "ready"
    return "offline"


def get(ctx, *positional, field=None):
    if positional:
        field = positional[0]

    data = {
        "status": status(ctx),
        "path": _STATE.get("path")
    }
    if field:
        return data.get(str(field).lower())
    return data


def list_dir(ctx, *positional, path=None):
    if positional:
        path = positional[0]
    path = _mount_path(path or _STATE.get("path") or "/sd")
    try:
        return os_lib.listdir(path)
    except Exception as e:
        ctx.log("SD list failed: %s" % e, "ERROR")
        return []


def get_module():
    return {
        "mount": mount,
        "unmount": unmount,
        "status": status,
        "get": get,
        "list": list_dir
    }


def get_manifest():
    return {
        "name": "sd_spi",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["storage-driver", "sdcard", "spi"]
    }
