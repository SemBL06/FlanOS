import builtins
from modules.system import get_display_size


def capitalize_words(value):
    text = str(value).replace("_", " ").replace("-", " ")
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


def get_label(item, field=None):
    if isinstance(item, dict):
        if field and field in item:
            return item.get(field)

        for key in ("name", "ssid", "title", "label", "id"):
            if key in item:
                return item.get(key)

    return item


def get_display_module(ctx):
    executor = getattr(ctx, "executor", None)
    if executor is None:
        return {}

    module = executor.modules.get("display")
    if isinstance(module, dict):
        return module

    return {}


def has_display(ctx):
    display = get_display_module(ctx)
    checker = display.get("available")
    if callable(checker):
        try:
            return bool(checker(ctx))
        except:
            return False
    return False


def display_clear(ctx):
    if not has_display(ctx):
        return

    display = get_display_module(ctx)
    clearer = display.get("clear")
    if callable(clearer):
        clearer(ctx)


def display_print(ctx, text, y):
    if not has_display(ctx):
        return

    display = get_display_module(ctx)
    printer = display.get("print")
    if callable(printer):
        printer(ctx, text=text, x=0, y=y)


def get_clicked(ctx):
    executor = getattr(ctx, "executor", None)
    if executor is None:
        return ""

    controls = executor.modules.get("controls")
    if isinstance(controls, dict):
        getter = controls.get("clicked")
        if callable(getter):
            return getter(ctx)

    button = executor.modules.get("button")
    if isinstance(button, dict):
        getter = button.get("get")
        if callable(getter):
            return getter(ctx, "clicked")

    return ""


def get_pressed_name(ctx):
    executor = getattr(ctx, "executor", None)
    if executor is None:
        return ""

    previous = ctx.vars.get("_ui_button_prev", {})
    if not isinstance(previous, dict):
        previous = {}

    controls = executor.modules.get("controls")
    if not isinstance(controls, dict):
        return ""

    pressed = controls.get("pressed")
    if not callable(pressed):
        return ""

    names = ("up", "down", "left", "right")
    i = 0
    while i < len(names):
        name = names[i]
        i += 1
        try:
            current = bool(pressed(ctx, state=name))
        except:
            current = False
        prior = bool(previous.get(name, False))
        previous[name] = current
        if current and not prior:
            ctx.vars["_ui_button_prev"] = previous
            return name

    ctx.vars["_ui_button_prev"] = previous
    return ""


def get_navigation_input(ctx):
    pressed_name = get_pressed_name(ctx)
    if pressed_name:
        return pressed_name
    return get_clicked(ctx)


def store_cursor(ctx, items, selected, field=None, marker="*", right_action="back"):
    item = items[selected]
    ctx.vars["_cursor"] = {
        "items": items,
        "index": selected,
        "field": field,
        "marker": marker,
        "right_action": right_action,
        "item": item
    }

    return item


def get_cursor_state(ctx):
    state = ctx.vars.get("_cursor", {})
    if not isinstance(state, dict):
        return {}
    return state


def wrap_index(index, size):
    if size <= 0:
        return 0
    return index % size


def render_options(ctx, items, selected, field=None, marker="*", right_action="back"):
    if not isinstance(items, list) or not items:
        ctx.log("No options available", "ERROR")
        return None

    selected = wrap_index(selected, len(items))
    selected_item = store_cursor(ctx, items, selected, field, marker, right_action=right_action)
    size = get_display_size(ctx)
    visible = min(len(items), max(1, int(size.get("height", 2))))
    rendered = []

    if not has_display(ctx):
        ctx.vars["_options_last"] = []
        ctx.vars["_ui_last"] = {
            "mode": "options",
            "selected": selected
        }
        return selected_item

    display_clear(ctx)

    offset = 0
    lines = []
    while offset < visible:
        item_index = wrap_index(selected + offset, len(items))
        pointer = marker + ")" if offset == 0 else " )"
        label = get_label(items[item_index], field)
        line = "%s %s" % (pointer, label)
        lines.append(line)
        rendered.append({
            "text": line,
            "x": 0,
            "y": offset
        })
        offset += 1

    if lines:
        display_print(ctx, lines, 0)

    ctx.vars["_options_last"] = rendered
    ctx.vars["_ui_last"] = {
        "mode": "options",
        "selected": selected
    }
    return selected_item


def options_move(ctx, direction=None):
    state = get_cursor_state(ctx)
    items = state.get("items")

    if not isinstance(items, list) or not items:
        ctx.log("Cursor has no items", "ERROR")
        return None

    index = state.get("index", 0)
    direction = str(direction or "").lower()

    if direction == "up":
        index -= 1
    elif direction == "down":
        index += 1

    return render_options(
        ctx,
        items=items,
        selected=index,
        field=state.get("field"),
        marker=state.get("marker", "*"),
        right_action=state.get("right_action", "back")
    )


def options_current(ctx):
    state = get_cursor_state(ctx)
    return state.get("item")


def options_index(ctx):
    state = get_cursor_state(ctx)
    return state.get("index", 0)


def last_action(ctx):
    action = ctx.vars.get("_menu_last_action", "")
    if isinstance(action, str):
        return action
    return ""


def options(ctx, *positional, list=None, items=None, field=None, selected=None, marker="*", handle_input=True, right_action="back", right=None):
    ctx.vars["_menu_last_action"] = ""
    if right is not None:
        right_action = right

    if items is None:
        items = list
    if items is None and positional:
        items = positional[0]

    if items is not None:
        items = ctx.executor.resolve(items)
        if selected is None:
            selected = 0
        try:
            selected = int(ctx.executor.resolve(selected))
        except:
            selected = 0
        render_options(ctx, items, selected, field=field, marker=marker, right_action=right_action)
    else:
        state = get_cursor_state(ctx)
        items = state.get("items")
        if not isinstance(items, builtins.list) or not items:
            ctx.log("No menu items available", "ERROR")
            return None

    current_item = options_current(ctx)
    if not handle_input:
        return current_item

    clicked = get_navigation_input(ctx)
    if clicked == "up":
        return options_move(ctx, "up")
    if clicked == "down":
        return options_move(ctx, "down")
    if clicked == "left":
        ctx.vars["_menu_last_action"] = "select"
        return current_item
    if clicked == "right":
        current_action = str(get_cursor_state(ctx).get("right_action", right_action)).lower()
        if current_action in ("continue", "select", "run"):
            ctx.vars["_menu_last_action"] = "select"
            return current_item
        ctx.vars["_menu_last_action"] = "back"
        return "back"
    return current_item


def wrap_text(text, width):
    if width <= 0:
        return [str(text)]

    value = str(text if text is not None else "")
    if value == "":
        return [""]

    lines = []
    i = 0
    while i < len(value):
        lines.append(value[i:i + width])
        i += width
    return lines


def format_description_lines(value, width):
    lines = []

    if isinstance(value, dict):
        for key in value:
            line = "%s: %s" % (capitalize_words(key), value[key])
            parts = wrap_text(line, width)
            i = 0
            while i < len(parts):
                lines.append(parts[i])
                i += 1
        return lines

    if isinstance(value, list):
        i = 0
        while i < len(value):
            parts = wrap_text(value[i], width)
            j = 0
            while j < len(parts):
                lines.append(parts[j])
                j += 1
            i += 1
        return lines

    return wrap_text(value, width)


def description(ctx, *positional, value=None, text=None, title=None, handle_input=True):
    ctx.vars["_menu_last_action"] = ""

    if value is None:
        value = text
    if value is None and positional:
        value = positional[0]

    size = get_display_size(ctx)
    width = int(size.get("width", 16))
    height = max(1, int(size.get("height", 2)))
    body_lines = format_description_lines(value, width)
    body_start = 1 if title else 0
    page_size = max(1, height - body_start)

    state = ctx.vars.get("_ui_description", {})
    if not isinstance(state, dict):
        state = {}

    offset = state.get("offset", 0)
    clicked = get_navigation_input(ctx) if handle_input else ""
    if clicked == "up":
        offset -= page_size
    elif clicked == "down":
        offset += page_size
    elif clicked == "right":
        ctx.vars["_menu_last_action"] = "back"
        return "back"

    if offset < 0:
        offset = 0
    if offset >= len(body_lines):
        offset = 0

    rendered = {
        "title": None,
        "lines": []
    }

    if not has_display(ctx):
        ctx.vars["_description_last"] = rendered
        ctx.vars["_ui_description"] = {
            "offset": offset,
            "title": title,
            "value": value
        }
        ctx.vars["_ui_last"] = {
            "mode": "description",
            "offset": offset
        }
        return value

    display_clear(ctx)

    lines_to_draw = []
    if title:
        title_text = wrap_text(title, width)[0]
        lines_to_draw.append(title_text)
        rendered["title"] = {
            "text": title_text,
            "x": 0,
            "y": 0
        }

    line_index = 0
    while line_index < page_size:
        body_index = offset + line_index
        if body_index >= len(body_lines):
            break

        y = body_start + line_index
        line = body_lines[body_index]
        rendered["lines"].append({
            "text": line,
            "x": 0,
            "y": y
        })
        lines_to_draw.append(line)
        line_index += 1

    if lines_to_draw:
        display_print(ctx, lines_to_draw, 0)

    ctx.vars["_description_last"] = rendered
    ctx.vars["_ui_description"] = {
        "offset": offset,
        "title": title,
        "value": value
    }
    ctx.vars["_ui_last"] = {
        "mode": "description",
        "offset": offset
    }
    return value


def get_module():
    return {
        "options": options,
        "description": description,
        "current": options_current,
        "index": options_index,
        "action": last_action
    }
