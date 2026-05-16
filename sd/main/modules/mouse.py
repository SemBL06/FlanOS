from core.drivers.hid import BUTTON_ALIASES, get_backend, normalize_button
from core.utils.layout import resolve_position

EDGE_DISTANCE = 4000


def resolve_move_target(position):
    if not position:
        return None

    target = resolve_position(position=position, width=3, height=3)
    dx = 0
    dy = 0

    if target["x"] == 0:
        dx = -EDGE_DISTANCE
    elif target["x"] == 2:
        dx = EDGE_DISTANCE

    if target["y"] == 0:
        dy = -EDGE_DISTANCE
    elif target["y"] == 2:
        dy = EDGE_DISTANCE

    return dx, dy


def move(ctx, x=0, y=0, position=None):
    if position is not None:
        target = resolve_move_target(position)
        if target is None:
            ctx.log("Invalid mouse position", "ERROR")
            return None
        x, y = target

    try:
        x = int(x)
        y = int(y)
    except:
        ctx.log("Mouse move expects numeric x/y", "ERROR")
        return None

    backend = get_backend(ctx)
    if backend is not None:
        backend.mouse_move(x, y)

    ctx.vars["_mouse_last"] = {"action": "move", "x": x, "y": y, "position": position}
    ctx.log("Mouse move: x=%s y=%s" % (x, y))
    return {"x": x, "y": y}


def click(ctx, type="left"):
    button = normalize_button(type)
    backend = get_backend(ctx)
    if backend is not None:
        backend.mouse_click(button)

    ctx.vars["_mouse_last"] = {"action": "click", "button": button}
    ctx.log("Mouse click: %s" % button)
    return button


def hold(ctx, *positional, type="left"):
    if positional:
        type = positional[0]

    button = normalize_button(type)
    backend = get_backend(ctx)
    if backend is not None:
        backend.mouse_hold(button)

    ctx.vars["_mouse_last"] = {"action": "hold", "button": button}
    ctx.log("Mouse hold: %s" % button)
    return button


def release(ctx, *positional, type="left"):
    if positional and len(positional) == 1 and str(positional[0]).lower() == "all" and type == "left":
        return release_all(ctx)

    if positional:
        type = positional[0]

    button = normalize_button(type)
    backend = get_backend(ctx)
    if backend is not None:
        backend.mouse_release(button)

    ctx.vars["_mouse_last"] = {"action": "release", "button": button}
    ctx.log("Mouse release: %s" % button)
    return button


def release_all(ctx):
    backend = get_backend(ctx)
    if backend is not None:
        backend.mouse_release_all()

    ctx.vars["_mouse_last"] = {"action": "release_all"}
    ctx.log("Mouse release all")
    return True


def scroll(ctx, amount=0):
    try:
        amount = int(amount)
    except:
        amount = 0

    backend = get_backend(ctx)
    if backend is not None:
        backend.mouse_scroll(amount)

    ctx.vars["_mouse_last"] = {"action": "scroll", "amount": amount}
    ctx.log("Mouse scroll: %s" % amount)
    return amount


def get_module():
    return {
        "move": move,
        "click": click,
        "hold": hold,
        "release": release,
        "scroll": scroll
    }


def get_manifest():
    return {
        "name": "mouse",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["hid", "mouse", "extension-module"]
    }
