from core.utils.args import pick_arg


def concat(ctx, *positional, a=None, b=None):
    a = pick_arg(positional, 0, a, "")
    b = pick_arg(positional, 1, b, "")
    return str(a) + str(b)


def length(ctx, *positional, value=None):
    value = pick_arg(positional, 0, value)
    try:
        return len(value)
    except:
        return 0


def upper(ctx, *positional, value=None):
    value = pick_arg(positional, 0, value, "")
    return str(value).upper()


def lower(ctx, *positional, value=None):
    value = pick_arg(positional, 0, value, "")
    return str(value).lower()

def get_module():
    return {
        "concat": concat,
        "length": length,
        "upper": upper,
        "lower": lower
    }
