import time
try:
    import gc
except:
    gc = None
from core.utils.args import pick_arg
from core.utils.layout import resolve_position

try:
    import uos as fs
except:
    import os as fs


def join_path(base, name):
    if base.endswith("/"):
        return base + name
    return base + "/" + name


def is_dir(path):
    try:
        fs.listdir(path)
        return True
    except:
        return False


def sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except:
        time.sleep(ms / 1000)


def normalize_effect_duration(duration=None, seconds=None, default_ms=120):
    if seconds is not None:
        try:
            return max(10, int(float(seconds) * 1000))
        except:
            pass

    if duration is not None:
        try:
            return max(10, int(duration))
        except:
            pass

    return default_ms


def collect_scripts(path, results, prefix=""):
    try:
        entries = fs.listdir(path)
    except:
        return

    for name in entries:
        full_path = join_path(path, name)
        rel_path = join_path(prefix, name) if prefix else name

        if is_dir(full_path):
            collect_scripts(full_path, results, rel_path)
        elif name.endswith(".fl"):
            results.append({
                "name": format_script_name(rel_path),
                "path": full_path,
                "type": "script"
            })


def capitalize_words(value):
    text = str(value).replace("_", " ").replace("-", " ").replace("/", " ")
    parts = text.split(" ")
    result = []

    for part in parts:
        if not part:
            continue

        first = part[0].upper()
        if len(part) > 1:
            result.append(first + part[1:])
        else:
            result.append(first)

    return " ".join(result)


def format_script_name(rel_path):
    if rel_path.endswith("/main.fl"):
        rel_path = rel_path[:-8]
    elif rel_path == "main.fl":
        rel_path = "main"
    elif rel_path.endswith(".fl"):
        rel_path = rel_path[:-3]

    return capitalize_words(rel_path)

def emit_display(ctx, kind, payload):
    ctx.vars["_display_last"] = payload
    if ctx.vars.get("_display_debug"):
        ctx.log("[DISPLAY:%s] %s" % (kind, payload))


def get_display_provider(ctx):
    providers = ctx.vars.get("_providers", {})
    if isinstance(providers, dict):
        provider = providers.get("display")
        if isinstance(provider, dict):
            return provider
    return None


def display_available(ctx):
    provider = get_display_provider(ctx)
    if not isinstance(provider, dict):
        return False

    checker = provider.get("available")
    if callable(checker):
        try:
            return bool(checker(ctx))
        except:
            return False

    return True


def get_display_size(ctx):
    provider = get_display_provider(ctx)
    if isinstance(provider, dict):
        size = provider.get("size")
        if callable(size):
            try:
                current = size(ctx)
                if isinstance(current, dict):
                    width = int(current.get("width", 16))
                    height = int(current.get("height", 8))
                    return {"width": width, "height": height}
            except:
                pass

        try:
            width = int(provider.get("width", 16))
            height = int(provider.get("height", 8))
            return {"width": width, "height": height}
        except:
            pass

    return {"width": 16, "height": 8}


def call_display_provider(ctx, action, payload):
    provider = get_display_provider(ctx)
    if not isinstance(provider, dict):
        if not ctx.vars.get("_display_provider_missing_logged"):
            ctx.vars["_display_provider_missing_logged"] = True
            ctx.log("No display detected; skipping display commands", "WARN")
        return None

    ctx.vars["_display_provider_missing_logged"] = False
    func = provider.get(action)
    if not callable(func):
        return None

    return func(ctx, payload)


def get_display_effect(ctx):
    effect = ctx.vars.get("_display_effect")
    if isinstance(effect, dict):
        return effect
    return None


def clear_display_effect(ctx):
    ctx.vars["_display_effect"] = None


def display_effect(ctx, *positional, type=None, duration=None, seconds=None):
    effect_type = pick_arg(positional, 0, type, "none")
    duration = pick_arg(positional, 1, duration)
    seconds = pick_arg(positional, 2, seconds)
    normalized = {
        "type": str(effect_type).lower(),
        "duration": normalize_effect_duration(duration, seconds)
    }
    ctx.vars["_display_effect"] = normalized
    return normalized


def render_provider_lines(ctx, rendered):
    if not isinstance(rendered, list):
        return

    call_display_provider(ctx, "line", rendered)


def build_rendered_line(text, x, y, position, width, height):
    coords = resolve_position(x=x, y=y, position=position, text=text, width=width, height=height)
    return [{"text": text, "x": coords["x"], "y": coords["y"]}]


def apply_display_effect(ctx, rendered, x, y, position, width, height):
    effect = get_display_effect(ctx)
    if not effect or not isinstance(rendered, list) or len(rendered) != 1:
        return False

    effect_type = effect.get("type")
    delay = effect.get("duration", 120)
    item = rendered[0]
    text = str(item.get("text", ""))
    line_y = item.get("y", 0)

    if effect_type == "type":
        i = 1
        while i <= len(text):
            render_provider_lines(ctx, build_rendered_line(text[:i], x, line_y, position, width, height))
            sleep_ms(delay)
            i += 1
        clear_display_effect(ctx)
        return True

    if effect_type == "blink":
        blank = " " * min(width, max(1, len(text)))
        render_provider_lines(ctx, build_rendered_line(text, x, line_y, position, width, height))
        sleep_ms(delay)
        render_provider_lines(ctx, build_rendered_line(blank, x, line_y, position, width, height))
        sleep_ms(delay)
        render_provider_lines(ctx, build_rendered_line(text, x, line_y, position, width, height))
        clear_display_effect(ctx)
        return True

    if effect_type == "show":
        if len(text) <= width:
            clear_display_effect(ctx)
            return False
        i = 0
        while i <= len(text) - width:
            render_provider_lines(ctx, [{"text": text[i:i + width], "x": 0, "y": line_y}])
            sleep_ms(delay)
            i += 1
        clear_display_effect(ctx)
        return True

    if effect_type == "scroll":
        padded = " " * width + text + " " * width
        i = 0
        while i <= len(padded) - width:
            render_provider_lines(ctx, [{"text": padded[i:i + width], "x": 0, "y": line_y}])
            sleep_ms(delay)
            i += 1
        clear_display_effect(ctx)
        return True

    clear_display_effect(ctx)
    return False


def normalize_display_lines(value):
    if isinstance(value, list):
        result = []
        i = 0
        while i < len(value):
            result.append(str(value[i]))
            i += 1
        return result
    return [str(value if value is not None else "")]


def display_print(ctx, *positional, text=None, x=None, y=None, position=None):
    text = pick_arg(positional, 0, text, "")
    x = pick_arg(positional, 1, x, 0)
    y = pick_arg(positional, 2, y, 0)

    lines = normalize_display_lines(text)
    size = get_display_size(ctx)
    rendered = []
    i = 0
    while i < len(lines):
        current = lines[i]
        line_y = y if i == 0 else y + i
        rendered.extend(build_rendered_line(current, x, line_y, position, size["width"], size["height"]))
        i += 1

    emit_display(ctx, "line", rendered)
    if not apply_display_effect(ctx, rendered, x, y, position, size["width"], size["height"]):
        call_display_provider(ctx, "line", rendered)
    return text


def display_clear(ctx):
    emit_display(ctx, "clear", {"cleared": True})
    provided = call_display_provider(ctx, "clear", {"cleared": True})
    if provided is not None:
        return provided
    return True


def display_invert(ctx):
    state = not bool(ctx.vars.get("_display_inverted", False))
    ctx.vars["_display_inverted"] = state
    emit_display(ctx, "invert", {"inverted": state})
    provided = call_display_provider(ctx, "invert", {"inverted": state})
    if provided is not None:
        return provided
    return state


def display_shapes(ctx, *positional, shape=None, text=None, x=None, y=None, position=None):
    shape = pick_arg(positional, 0, shape, "BOX")
    text = pick_arg(positional, 1, text, "")
    size = get_display_size(ctx)
    coords = resolve_position(x=x, y=y, position=position, text=text, width=size["width"], height=size["height"])
    payload = {
        "shape": str(shape).upper(),
        "text": text,
        "x": coords["x"],
        "y": coords["y"]
    }
    emit_display(ctx, "shapes", payload)
    call_display_provider(ctx, "shapes", payload)
    return payload


def display_image(ctx, *positional, image=None, x=None, y=None, position=None):
    image = pick_arg(positional, 0, image)
    size = get_display_size(ctx)
    coords = resolve_position(x=x, y=y, position=position, width=size["width"], height=size["height"])
    cached = None

    if isinstance(image, str) and image.endswith(".png"):
        cached = image[:-4] + ".bin"
        try:
            with open(cached, "rb"):
                pass
        except:
            cached = None

    payload = {
        "image": image,
        "cached": cached,
        "x": coords["x"],
        "y": coords["y"]
    }
    emit_display(ctx, "image", payload)
    call_display_provider(ctx, "image", payload)
    return payload


def log_info(ctx, *positional, text=None):
    text = pick_arg(positional, 0, text, "")
    ctx.log(text, level="INFO")
    return text


def log_warn(ctx, *positional, text=None):
    text = pick_arg(positional, 0, text, "")
    ctx.log(text, level="WARN")
    return text


def log_debug(ctx, *positional, text=None):
    text = pick_arg(positional, 0, text, "")
    ctx.log(text, level="DEBUG")
    return text


def log_error(ctx, *positional, text=None):
    text = pick_arg(positional, 0, text, "")
    ctx.log(text, level="ERROR")
    return text


def system_sleep(ctx, *positional, ms=None):
    ms = pick_arg(positional, 0, ms, 0)
    try:
        ms = int(ms)
    except:
        ms = 0

    if ms < 0:
        ms = 0

    sleep_ms(ms)
    return ms


def system_gc(ctx):
    if gc is None or not hasattr(gc, "collect"):
        return {
            "available": False
        }

    try:
        gc.collect()
    except:
        pass

    data = {
        "available": True
    }
    if hasattr(gc, "mem_free"):
        try:
            data["free"] = gc.mem_free()
        except:
            pass
    if hasattr(gc, "mem_alloc"):
        try:
            data["used"] = gc.mem_alloc()
        except:
            pass
    return data


def system_memory(ctx):
    if gc is None:
        return {
            "available": False
        }

    data = {
        "available": hasattr(gc, "collect")
    }
    if hasattr(gc, "mem_free"):
        try:
            data["free"] = gc.mem_free()
        except:
            pass
    if hasattr(gc, "mem_alloc"):
        try:
            data["used"] = gc.mem_alloc()
        except:
            pass
    return data


def scripts(ctx, *positional, path=None):
    path = pick_arg(positional, 0, path, "/sd/scripts")
    results = []
    collect_scripts(path, results)

    if not results and isinstance(path, str) and path.startswith("/sd/"):
        collect_scripts(path[1:], results)

    i = 0
    while i < len(results):
        item = results[i]
        if isinstance(item, dict):
            current_path = item.get("path")
            if isinstance(current_path, str) and current_path.startswith("sd/"):
                item["path"] = "/" + current_path
        i += 1

    return results


def cursor(ctx, *positional):
    state = ctx.vars.get("_cursor", {})
    field = "position"

    if positional:
        field = str(positional[0]).lower()

    if field == "position":
        return state.get("item")
    if field == "index":
        return state.get("index", 0)
    if field == "marker":
        return state.get("marker", "*")

    return None


def resolve_script_target(ctx, target):
    if isinstance(target, dict):
        if target.get("type") == "script":
            return target.get("path")
        return None

    if isinstance(target, str):
        if target == "selected":
            state = ctx.vars.get("_cursor", {})
            return resolve_script_target(ctx, state.get("item"))
        return target

    return None


def run(ctx, *positional, script=None):
    target = script

    if target is None and positional:
        target = positional[0]

    if target != "selected":
        target = ctx.executor.resolve(target)

    path = resolve_script_target(ctx, target)

    if not path and script is None and positional:
        state = ctx.vars.get("_cursor", {})
        path = resolve_script_target(ctx, state.get("item"))

    if not path:
        ctx.log("No script selected to run", "ERROR")
        return None

    ctx.log("Running script: %s" % path)
    if gc is not None:
        try:
            gc.collect()
        except:
            pass
    try:
        ctx.executor.execute_script(path)
    finally:
        if gc is not None:
            try:
                gc.collect()
            except:
                pass
    return path


def get_module():
    return {
        "print": display_print,   # display print ...
        "clear": display_clear,
        "invert": display_invert,
        "available": display_available,
        "effect": display_effect,
        "shapes": display_shapes,
        "image": display_image,
        "info": log_info,         # log info ...
        "warn": log_warn,
        "debug": log_debug,
        "error": log_error,       # log error ...
        "sleep": system_sleep,    # system sleep 1000
        "gc": system_gc,
        "memory": system_memory,
        "scripts": scripts,       # system scripts
        "cursor": cursor,         # system cursor position/index/marker
        "run": run                # system run selected/script=...
    }
