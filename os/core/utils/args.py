def pick_arg(positional, index, current=None, default=None):
    if current is not None:
        return current

    if positional and index < len(positional):
        return positional[index]

    return default
