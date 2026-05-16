try:
    import usb_hid
except:
    usb_hid = None

try:
    from adafruit_hid.keyboard import Keyboard as USBKeyboard
    from adafruit_hid.keycode import Keycode
    from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
except:
    USBKeyboard = None
    Keycode = None
    KeyboardLayoutUS = None

try:
    from adafruit_hid.mouse import Mouse as USBMouse
except:
    USBMouse = None


KEY_ALIASES = {
    "SUPER": "WINDOWS",
    "GUI": "WINDOWS",
    "WIN": "WINDOWS",
    "CTRL": "CONTROL",
    "RETURN": "ENTER",
    "ESC": "ESCAPE",
    "UP": "UP_ARROW",
    "DOWN": "DOWN_ARROW",
    "LEFT": "LEFT_ARROW",
    "RIGHT": "RIGHT_ARROW",
    "SPACE": "SPACEBAR"
}

NUMBER_KEYS = {
    "0": "ZERO",
    "1": "ONE",
    "2": "TWO",
    "3": "THREE",
    "4": "FOUR",
    "5": "FIVE",
    "6": "SIX",
    "7": "SEVEN",
    "8": "EIGHT",
    "9": "NINE"
}

BUTTON_ALIASES = {
    "left": 1,
    "middle": 2,
    "right": 4
}

AUTO_BACKEND = None


def sleep_ms(ms):
    import time

    try:
        time.sleep_ms(ms)
    except:
        time.sleep(ms / 1000)


def normalize_key_name(value):
    text = str(value).upper()
    text = KEY_ALIASES.get(text, text)
    text = NUMBER_KEYS.get(text, text)
    return text


def normalize_keys(value):
    if isinstance(value, list):
        result = []
        i = 0

        while i < len(value):
            result.extend(normalize_keys(value[i]))
            i += 1

        return result

    if value is None:
        return []

    return [normalize_key_name(value)]


def normalize_button(value):
    if value is None:
        return "left"

    text = str(value).lower()
    return text


class CircuitPythonHIDBackend:
    def __init__(self):
        self.keyboard = USBKeyboard(usb_hid.devices)
        self.layout = KeyboardLayoutUS(self.keyboard) if KeyboardLayoutUS else None
        self.mouse = USBMouse(usb_hid.devices) if USBMouse else None

    def resolve_keycodes(self, keys):
        codes = []
        i = 0

        while i < len(keys):
            key = normalize_key_name(keys[i])
            code = getattr(Keycode, key, None)
            if code is None:
                raise ValueError("Unknown HID key: %s" % keys[i])
            codes.append(code)
            i += 1

        return codes

    def keyboard_hold(self, keys):
        self.keyboard.press(*self.resolve_keycodes(keys))

    def keyboard_release(self, keys):
        self.keyboard.release(*self.resolve_keycodes(keys))

    def keyboard_release_all(self):
        self.keyboard.release_all()

    def keyboard_type(self, text):
        if self.layout is None:
            raise ValueError("Keyboard text typing unavailable")
        self.layout.write(text)

    def keyboard_press(self, keys, delay_ms):
        codes = self.resolve_keycodes(keys)
        self.keyboard.press(*codes)
        sleep_ms(delay_ms)
        self.keyboard.release(*codes)

    def mouse_move(self, x, y):
        if self.mouse is None:
            raise ValueError("Mouse unavailable")

        while x or y:
            step_x = max(-127, min(127, x))
            step_y = max(-127, min(127, y))
            self.mouse.move(x=step_x, y=step_y)
            x -= step_x
            y -= step_y

    def mouse_click(self, button):
        if self.mouse is None:
            raise ValueError("Mouse unavailable")

        self.mouse.click(button=self.resolve_button(button))

    def mouse_hold(self, button):
        if self.mouse is None:
            raise ValueError("Mouse unavailable")

        self.mouse.press(self.resolve_button(button))

    def mouse_release(self, button):
        if self.mouse is None:
            raise ValueError("Mouse unavailable")

        self.mouse.release(self.resolve_button(button))

    def mouse_release_all(self):
        if self.mouse is None:
            raise ValueError("Mouse unavailable")

        for button in (1, 2, 4):
            try:
                self.mouse.release(button)
            except:
                pass

    def mouse_scroll(self, amount):
        if self.mouse is None:
            raise ValueError("Mouse unavailable")

        self.mouse.move(wheel=int(amount))

    def resolve_button(self, button):
        name = normalize_button(button)
        if name == "left":
            return USBMouse.LEFT_BUTTON
        if name == "middle":
            return USBMouse.MIDDLE_BUTTON
        if name == "right":
            return USBMouse.RIGHT_BUTTON
        raise ValueError("Unknown mouse button: %s" % button)


def get_backend(ctx):
    global AUTO_BACKEND

    backend = getattr(ctx, "hid", None)
    if backend is not None:
        return backend

    if AUTO_BACKEND is not None:
        return AUTO_BACKEND

    if usb_hid is not None and USBKeyboard is not None and Keycode is not None:
        try:
            AUTO_BACKEND = CircuitPythonHIDBackend()
            return AUTO_BACKEND
        except:
            return None

    return None
