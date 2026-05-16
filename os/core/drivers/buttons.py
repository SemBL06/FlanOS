try:
    import machine
except:
    machine = None

from core.storage.config import ensure_main_config

BUTTON_NAMES = ("up", "down", "left", "right")
AUTO_BACKEND = None
AUTO_BACKEND_ERROR = ""


class MachineButtonBackend:
    def __init__(self, config):
        self.config = config
        self.buttons = {}
        self.previous = {}

        button_config = config.get("buttons", {})
        buttons_active_low = button_config.get("buttons_active_low", True)

        i = 0
        while i < len(BUTTON_NAMES):
            name = BUTTON_NAMES[i]
            i += 1
            pin = button_config.get(name)

            if pin is None:
                continue

            pull = machine.Pin.PULL_UP if buttons_active_low else machine.Pin.PULL_DOWN
            self.buttons[name] = machine.Pin(pin, machine.Pin.IN, pull)
            self.previous[name] = self.get_state(name)

    def get_config_snapshot(self):
        button_config = self.config.get("buttons", {})
        snapshot = {
            "buttons_active_low": bool(button_config.get("buttons_active_low", True))
        }

        i = 0
        while i < len(BUTTON_NAMES):
            name = BUTTON_NAMES[i]
            i += 1
            snapshot[name] = button_config.get(name)

        return snapshot

    def get_state(self, name):
        button = self.buttons.get(name)
        if button is None:
            return False

        value = button.value()
        button_config = self.config.get("buttons", {})

        buttons_active_low = button_config.get("buttons_active_low", True)
        return not bool(value) if buttons_active_low else bool(value)

    def get_raw(self, name):
        button = self.buttons.get(name)
        if button is None:
            return None
        try:
            return int(button.value())
        except:
            return None

    def get_debug_snapshot(self):
        snapshot = {}
        i = 0
        while i < len(BUTTON_NAMES):
            name = BUTTON_NAMES[i]
            i += 1
            snapshot[name] = {
                "raw": self.get_raw(name),
                "pressed": self.get_state(name),
                "previous": bool(self.previous.get(name, False))
            }
        return snapshot

    def get_clicked(self):
        i = 0
        while i < len(BUTTON_NAMES):
            name = BUTTON_NAMES[i]
            i += 1

            current = self.get_state(name)
            previous = self.previous.get(name, False)
            self.previous[name] = current

            if current and not previous:
                return name

        return ""


def reset_backend():
    global AUTO_BACKEND, AUTO_BACKEND_ERROR
    AUTO_BACKEND = None
    AUTO_BACKEND_ERROR = ""


def probe_pin(pin, active_low=True, pull="up"):
    if machine is None:
        return {
            "available": False,
            "error": "machine unavailable",
            "pin": pin,
            "raw": None,
            "pressed": False
        }

    try:
        pin_number = int(pin)
    except:
        return {
            "available": False,
            "error": "invalid pin",
            "pin": pin,
            "raw": None,
            "pressed": False
        }

    pull_mode = None
    try:
        pull_name = str(pull or "up").lower()
    except:
        pull_name = "up"

    if pull_name == "down":
        pull_mode = machine.Pin.PULL_DOWN
    else:
        pull_mode = machine.Pin.PULL_UP

    try:
        current = machine.Pin(pin_number, machine.Pin.IN, pull_mode)
        raw = int(current.value())
        if active_low:
            pressed = not bool(raw)
        else:
            pressed = bool(raw)
        return {
            "available": True,
            "error": "",
            "pin": pin_number,
            "raw": raw,
            "pressed": pressed
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "pin": pin_number,
            "raw": None,
            "pressed": False
        }


def get_backend(ctx):
    global AUTO_BACKEND, AUTO_BACKEND_ERROR

    backend = getattr(ctx, "buttons", None)
    if backend is not None:
        return backend

    if AUTO_BACKEND is not None:
        return AUTO_BACKEND

    if machine is None:
        AUTO_BACKEND_ERROR = "machine unavailable"
        return None

    try:
        AUTO_BACKEND = MachineButtonBackend(ensure_main_config())
        AUTO_BACKEND_ERROR = ""
        return AUTO_BACKEND
    except Exception as e:
        AUTO_BACKEND_ERROR = str(e)
        return None


def get_backend_status(ctx):
    backend = get_backend(ctx)

    if backend is None:
        return {
            "available": False,
            "error": AUTO_BACKEND_ERROR,
            "config": ensure_main_config().get("buttons", {}),
            "state": {}
        }

    return {
        "available": True,
        "error": "",
        "config": backend.get_config_snapshot(),
        "state": backend.get_debug_snapshot()
    }
