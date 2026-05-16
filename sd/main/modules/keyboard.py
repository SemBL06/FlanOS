from core.drivers.hid import get_backend, normalize_keys, sleep_ms


def format_keys(keys):
    return "+".join(keys)


def hold(ctx, *positional, key=None):
    keys = []

    if positional:
        keys.extend(normalize_keys(list(positional)))
    keys.extend(normalize_keys(key))

    if not keys:
        ctx.log("Missing keyboard key", "ERROR")
        return None

    backend = get_backend(ctx)
    if backend is not None:
        backend.keyboard_hold(keys)

    ctx.vars["_keyboard_last"] = {"action": "hold", "keys": keys}
    ctx.log("Keyboard hold: %s" % format_keys(keys))
    return keys


def release(ctx, *positional, key=None):
    if positional and len(positional) == 1 and str(positional[0]).lower() == "all" and key is None:
        return release_all(ctx)

    keys = []

    if positional:
        keys.extend(normalize_keys(list(positional)))
    keys.extend(normalize_keys(key))

    if not keys:
        ctx.log("Missing keyboard key", "ERROR")
        return None

    backend = get_backend(ctx)
    if backend is not None:
        backend.keyboard_release(keys)

    ctx.vars["_keyboard_last"] = {"action": "release", "keys": keys}
    ctx.log("Keyboard release: %s" % format_keys(keys))
    return keys


def release_all(ctx):
    backend = get_backend(ctx)
    if backend is not None:
        backend.keyboard_release_all()

    ctx.vars["_keyboard_last"] = {"action": "release_all"}
    ctx.log("Keyboard release all")
    return True


def print_text(ctx, text=""):
    backend = get_backend(ctx)
    if backend is not None:
        backend.keyboard_type(str(text))

    ctx.vars["_keyboard_last"] = {"action": "print", "text": str(text)}
    ctx.log('Keyboard print: "%s"' % text)
    return text

def press(ctx, *positional, key=None, delay=40):
    keys = []

    if positional:
        keys.extend(normalize_keys(list(positional)))
    keys.extend(normalize_keys(key))

    if not keys:
        ctx.log("Missing keyboard key", "ERROR")
        return None

    try:
        delay = int(delay)
    except:
        delay = 40

    backend = get_backend(ctx)
    if backend is not None:
        backend.keyboard_press(keys, delay)
    else:
        sleep_ms(delay)

    ctx.vars["_keyboard_last"] = {"action": "press", "keys": keys, "delay": delay}
    ctx.log("Keyboard press: %s" % format_keys(keys))
    return keys


def get_module():
    return {
        "hold": hold,
        "release": release,
        "print": print_text,
        "press": press
    }


def get_manifest():
    return {
        "name": "keyboard",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["hid", "keyboard", "extension-module"]
    }
