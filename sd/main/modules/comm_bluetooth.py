try:
    import bluetooth as bluetooth_lib
except:
    bluetooth_lib = None

try:
    import ubinascii as binascii_lib
except:
    import binascii as binascii_lib

import time
from core.utils.vendor import guess_vendor

_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6
_ble = None


def sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except:
        time.sleep(ms / 1000)


def normalize_duration(duration=None, seconds=None, default_ms=3000):
    if seconds is not None:
        try:
            return max(1000, int(float(seconds) * 1000))
        except:
            pass

    if duration is not None:
        try:
            return max(250, int(duration))
        except:
            pass

    return default_ms


def get_addr_type(value):
    mapping = {
        0: "PUBLIC",
        1: "RANDOM"
    }
    return mapping.get(value, "UNKNOWN")


def decode_name(payload):
    i = 0

    while i < len(payload):
        length = payload[i]

        if length == 0:
            break

        end = i + 1 + length

        if end > len(payload):
            break

        data_type = payload[i + 1]

        if data_type in (0x08, 0x09):
            raw = payload[i + 2:end]
            try:
                raw = bytes(raw)
            except:
                pass
            try:
                return raw.decode()
            except:
                try:
                    return str(raw, "utf-8")
                except:
                    return ""

        i = end

    return ""


def format_addr(addr):
    raw = binascii_lib.hexlify(addr)

    if not isinstance(raw, str):
        raw = raw.decode()

    parts = []
    i = 0

    while i < len(raw):
        parts.append(raw[i:i + 2])
        i += 2

    return ":".join(parts)


def get_ble(ctx):
    global _ble

    if bluetooth_lib is None:
        ctx.log("Bluetooth unavailable", "ERROR")
        return None

    if _ble is None:
        _ble = bluetooth_lib.BLE()
        _ble.active(True)

    return _ble


def merge_device(results, device):
    for existing in results:
        if existing["addr"] == device["addr"]:
            if device["name"] and existing["name"] == "UNKNOWN":
                existing["name"] = device["name"]

            existing["rssi"] = device["rssi"]
            existing["type"] = device["type"]
            existing["addr_type"] = device["addr_type"]
            existing["adv_type"] = device["adv_type"]
            return

    results.append(device)


def scan(ctx, duration=None, seconds=None):
    ctx.log("Scanning Bluetooth...")

    ble = get_ble(ctx)
    if ble is None:
        return []

    duration = normalize_duration(duration, seconds)

    results = []
    state = {"done": False}

    def irq(event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            name = decode_name(adv_data)

            merge_device(results, {
                "name": name or "UNKNOWN",
                "addr": format_addr(addr),
                "addr_type": addr_type,
                "type": get_addr_type(addr_type),
                "rssi": rssi,
                "adv_type": adv_type
            })

        elif event == _IRQ_SCAN_DONE:
            state["done"] = True

    ble.irq(irq)

    try:
        ble.gap_scan(duration, 30000, 30000, True)

        elapsed = 0
        while elapsed < duration + 200 and not state["done"]:
            sleep_ms(100)
            elapsed += 100

        try:
            ble.gap_scan(None)
        except:
            pass

        ctx.log("Found %s bluetooth devices" % len(results))
        return results

    except Exception as e:
        ctx.log("Bluetooth scan failed: %s" % e, "ERROR")
        return []


def get(ctx, *positional, device=None):
    if not positional:
        ctx.log("Missing field", "ERROR")
        return None

    field = str(positional[0]).lower()
    current = ctx.executor.resolve(device)

    if isinstance(current, dict):
        if field == "vendor":
            return guess_vendor(current.get("addr"))

        if field == "type" and len(positional) > 1:
            subtype = str(positional[1]).lower()
            if subtype == "vendor":
                return guess_vendor(current.get("addr"))
        return current.get(field)

    ctx.log("Invalid device object", "ERROR")
    return None

def get_comm_provider(ctx):
    return {
        "scan": scan,
        "get": get
    }


def get_manifest():
    return {
        "name": "bluetooth",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["comm-provider", "bluetooth", "extension-module"]
    }
