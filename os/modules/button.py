from core.utils.args import pick_arg
from core.drivers.buttons import BUTTON_NAMES, get_backend, get_backend_status, probe_pin, reset_backend


def normalize_type(value):
    if value is None:
        return ""

    return str(value).lower()


def button_name(name):
    def inner(ctx):
        return name
    return inner


def get(ctx, *positional, state=None, type=None):
    if not positional:
        if state is not None:
            return normalize_type(state)
        if type is not None:
            return normalize_type(type)
        ctx.log("Missing button field", "ERROR")
        return None

    field = str(positional[0]).lower()
    backend = get_backend(ctx)

    if field == "clicked":
        if backend is None:
            return ""

        clicked = backend.get_clicked()
        if clicked:
            ctx.vars["_button_last_clicked"] = clicked
        return clicked

    if field == "state":
        button_type = pick_arg(positional, 1, state)
        if button_type is None:
            button_type = type
        return normalize_type(button_type)

    if field == "pressed":
        button_type = pick_arg(positional, 1, state)
        if button_type is None:
            button_type = type
        button_type = normalize_type(button_type)

        if button_type not in BUTTON_NAMES:
            return False

        if backend is None:
            return False

        return backend.get_state(button_type)

    if field == "raw":
        button_type = pick_arg(positional, 1, state)
        if button_type is None:
            button_type = type
        button_type = normalize_type(button_type)

        if button_type not in BUTTON_NAMES:
            return None

        if backend is None:
            return None

        return backend.get_raw(button_type)

    if field == "debug":
        return get_backend_status(ctx)

    if field == "available":
        return bool(backend is not None)

    if field == "probe":
        pin_value = pick_arg(positional, 1, state)
        if pin_value is None:
            pin_value = type
        active_low = True
        pull = "up"
        return probe_pin(pin_value, active_low=active_low, pull=pull)

    if field == "reset":
        reset_backend()
        return True

    return None


def get_module():
    return {
        "get": get,
        "debug": lambda ctx: get(ctx, "debug"),
        "available": lambda ctx: get(ctx, "available"),
        "probe": lambda ctx, pin=None: get(ctx, "probe", pin),
        "reset": lambda ctx: get(ctx, "reset"),
        "left": button_name("left"),
        "right": button_name("right"),
        "up": button_name("up"),
        "down": button_name("down")
    }
