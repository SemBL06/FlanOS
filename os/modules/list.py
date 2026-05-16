from core.utils.args import pick_arg


def clone_items(items):
    if isinstance(items, list):
        return list(items)
    return []


def resolve_items(ctx, positional, items=None, allow_empty=False):
    if items is None and positional:
        items = positional[0]

    resolved = ctx.executor.resolve(items)

    if allow_empty and isinstance(items, str) and items == resolved and items not in ctx.vars:
        return []

    if resolved is None and allow_empty:
        return []

    if isinstance(resolved, list):
        return clone_items(resolved)

    if allow_empty and resolved is None:
        return []

    return None


def add(ctx, *positional, items=None, value=None):
    if value is None:
        if len(positional) > 1:
            value = positional[1]
        elif items is None and positional:
            value = positional[0]

    current = resolve_items(ctx, positional, items=items, allow_empty=True)
    if current is None:
        ctx.log("List add expects a list", "ERROR")
        return None

    current.append(ctx.executor.resolve(value))
    return current


def remove(ctx, *positional, items=None, value=None):
    if value is None and len(positional) > 1:
        value = positional[1]

    current = resolve_items(ctx, positional, items=items)
    if current is None:
        ctx.log("List remove expects a list", "ERROR")
        return None

    resolved_value = ctx.executor.resolve(value)
    result = []
    removed = False
    i = 0
    while i < len(current):
        item = current[i]
        if not removed and item == resolved_value:
            removed = True
        else:
            result.append(item)
        i += 1

    return result


def contains(ctx, *positional, items=None, value=None):
    if value is None and len(positional) > 1:
        value = positional[1]

    current = resolve_items(ctx, positional, items=items)
    if current is None:
        ctx.log("List contains expects a list", "ERROR")
        return False

    return ctx.executor.resolve(value) in current


def get(ctx, *positional, items=None, index=None):
    if index is None and len(positional) > 1:
        index = positional[1]

    current = resolve_items(ctx, positional, items=items)
    if current is None:
        ctx.log("List get expects a list", "ERROR")
        return None

    index = pick_arg((), 0, index, 0)
    try:
        index = int(ctx.executor.resolve(index))
    except:
        return None

    if index < 0 or index >= len(current):
        return None

    return current[index]


def length(ctx, *positional, items=None):
    current = resolve_items(ctx, positional, items=items)
    if current is None:
        ctx.log("List length expects a list", "ERROR")
        return 0

    return len(current)


def get_module():
    return {
        "add": add,
        "remove": remove,
        "contains": contains,
        "get": get,
        "length": length
    }
