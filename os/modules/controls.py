import modules.button as button_module


def get(ctx, *positional, state=None, type=None):
    return button_module.get(ctx, *positional, state=state, type=type)


def clicked(ctx):
    return button_module.get(ctx, "clicked")


def pressed(ctx, *positional, state=None, type=None):
    return button_module.get(ctx, "pressed", *positional, state=state, type=type)


def state_value(ctx, *positional, state=None, type=None):
    return button_module.get(ctx, "state", *positional, state=state, type=type)


def raw(ctx, *positional, state=None, type=None):
    return button_module.get(ctx, "raw", *positional, state=state, type=type)


def debug(ctx):
    return button_module.get(ctx, "debug")


def available(ctx):
    return button_module.get(ctx, "available")


def probe(ctx, *positional, pin=None):
    if pin is None and positional:
        pin = positional[0]
    return button_module.get(ctx, "probe", pin)


def reset(ctx):
    return button_module.get(ctx, "reset")


def get_module():
    return {
        "get": get,
        "clicked": clicked,
        "pressed": pressed,
        "state": state_value,
        "raw": raw,
        "debug": debug,
        "available": available,
        "probe": probe,
        "reset": reset,
        "left": button_module.button_name("left"),
        "right": button_module.button_name("right"),
        "up": button_module.button_name("up"),
        "down": button_module.button_name("down")
    }
