DISPLAY_WIDTH = 16
DISPLAY_HEIGHT = 8


def normalize_keyword(value):
    if value is None:
        return None
    return str(value).lower().replace("-", "_").replace(" ", "_")


def text_start_x(value, width=DISPLAY_WIDTH):
    text = str(value or "")
    length = len(text)
    if length >= width:
        return 0
    return max(0, (width - length) // 2)


def resolve_axis(value, axis, text=None, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT):
    if isinstance(value, int):
        return value

    try:
        return int(value)
    except:
        pass

    keyword = normalize_keyword(value)
    if keyword is None:
        return 0

    if axis == "x":
        if keyword == "left":
            return 0
        if keyword == "center":
            return text_start_x(text, width)
        if keyword == "right":
            return max(0, width - 1)
    else:
        if keyword == "top":
            return 0
        if keyword == "center":
            return max(0, height // 2)
        if keyword == "bottom":
            return max(0, height - 1)

    return 0


def resolve_position(x=0, y=0, position=None, text=None, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT):
    keyword = normalize_keyword(position)

    if keyword:
        parts = keyword.split("_")
        if "left" in parts:
            x = "left"
        elif "right" in parts:
            x = "right"
        elif "center" in parts:
            x = "center"

        if "top" in parts:
            y = "top"
        elif "bottom" in parts:
            y = "bottom"
        elif "center" in parts:
            y = "center"

    return {
        "x": resolve_axis(x, "x", text=text, width=width, height=height),
        "y": resolve_axis(y, "y", text=text, width=width, height=height)
    }
