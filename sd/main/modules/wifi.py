try:
    import network
except:
    network = None

try:
    import ubinascii
except:
    import binascii as ubinascii

from core.utils.vendor import guess_vendor
import time

if network is not None:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
else:
    wlan = None


# --- SECURITY TYPE MAPPING ---
def get_security_type(sec):
    types = {
        0: "OPEN",
        1: "WEP",
        2: "WPA-PSK",
        3: "WPA2-PSK",
        4: "WPA/WPA2-PSK"
    }
    return types.get(sec, "UNKNOWN")


# --- SCAN ---
def sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except:
        time.sleep(ms / 1000)


def normalize_duration(duration=None, seconds=None, default_ms=1500):
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


def merge_network(results, item):
    i = 0
    while i < len(results):
        current = results[i]
        if current.get("bssid") == item.get("bssid"):
            if item.get("rssi", -999) > current.get("rssi", -999):
                results[i] = item
            return
        i += 1

    results.append(item)


def scan(ctx, duration=None, seconds=None):
    ctx.log("Scanning WiFi...")

    results = []

    if wlan is None:
        ctx.log("WiFi unavailable", "ERROR")
        return results

    try:
        total_ms = normalize_duration(duration, seconds)
        started = time.time()
        elapsed_ms = 0

        while elapsed_ms < total_ms:
            nets = wlan.scan()

            for net in nets:
                ssid = net[0].decode()
                bssid = ubinascii.hexlify(net[1]).decode()
                channel = net[2]
                rssi = net[3]
                security = get_security_type(net[4])

                merge_network(results, {
                    "ssid": ssid,
                    "bssid": bssid,
                    "channel": channel,
                    "rssi": rssi,
                    "type": security
                })

            if total_ms <= 1500:
                break

            sleep_ms(250)
            elapsed_ms = int((time.time() - started) * 1000)

        ctx.log("Found %s networks" % len(results))
        return results

    except Exception as e:
        ctx.log(f"WiFi scan failed: {e}", "ERROR")
        return []


# --- GET PROPERTY ---
def get(ctx, *positional, network=None):
    if not positional:
        ctx.log("Missing field", "ERROR")
        return None

    field = str(positional[0]).lower()

    net = ctx.executor.resolve(network)

    if isinstance(net, dict):
        if field == "vendor":
            return guess_vendor(net.get("bssid"))

        if field == "type" and len(positional) > 1:
            subtype = str(positional[1]).lower()
            if subtype == "vendor":
                return guess_vendor(net.get("bssid"))
        return net.get(field)

    ctx.log("Invalid network object", "ERROR")
    return None

def get_comm_provider(ctx):
    return {
        "scan": scan,
        "get": get
    }


def get_manifest():
    return {
        "name": "wifi",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["comm-provider", "wifi", "extension-module"]
    }
