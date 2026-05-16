try:
    import network
except:
    network = None

try:
    import time
except:
    time = None

from core.storage.config import ensure_main_config


def _sleep_ms(ms):
    if time is None:
        return
    try:
        time.sleep_ms(ms)
    except:
        try:
            time.sleep(ms / 1000)
        except:
            pass


def ensure_wifi(ctx, label="network"):
    if network is None:
        return False

    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
    except:
        return False

    try:
        if wlan.isconnected():
            return True
    except:
        pass

    config = ensure_main_config()
    wifi = config.get("wifi", {})
    if not isinstance(wifi, dict):
        return False

    ssid = wifi.get("SSID")
    password = wifi.get("Password", "")
    if not ssid:
        return False

    try:
        ctx.log("Connecting WiFi for %s..." % label)
        wlan.connect(ssid, password)
    except Exception as e:
        ctx.log("%s WiFi connect failed: %s" % (str(label).capitalize(), e), "ERROR")
        return False

    waited = 0
    while waited < 10000:
        try:
            if wlan.isconnected():
                return True
        except:
            break
        _sleep_ms(250)
        waited += 250

    ctx.log("%s WiFi connect timed out" % str(label).capitalize(), "WARN")
    return False


def get_ip_address(default_value="127.0.0.1"):
    if network is not None:
        try:
            wlan = network.WLAN(network.STA_IF)
            if wlan.isconnected():
                return wlan.ifconfig()[0]
        except:
            pass

    return default_value
