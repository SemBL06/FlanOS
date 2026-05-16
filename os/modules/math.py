from core.utils.args import pick_arg


def add(ctx, *positional, a=None, b=None):
    a = pick_arg(positional, 0, a)
    b = pick_arg(positional, 1, b)
    return a + b


def sub(ctx, *positional, a=None, b=None):
    a = pick_arg(positional, 0, a)
    b = pick_arg(positional, 1, b)
    return a - b


def mul(ctx, *positional, a=None, b=None):
    a = pick_arg(positional, 0, a)
    b = pick_arg(positional, 1, b)
    return a * b


def div(ctx, *positional, a=None, b=None):
    a = pick_arg(positional, 0, a)
    b = pick_arg(positional, 1, b)
    try:
        return a / b
    except:
        return None

def get_module():
    return {
        "add": add,
        "sub": sub,
        "mul": mul,
        "div": div,
    }
