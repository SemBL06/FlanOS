from core.storage.config import ensure_main_config


def get_capability_provider(ctx, kind, name):
    store = ctx.vars.get("_capability_providers", {})
    if not isinstance(store, dict):
        return None

    bucket = store.get(kind, {})
    if not isinstance(bucket, dict):
        return None

    return bucket.get(name)


def get_device_config(kind, name):
    config = ensure_main_config()
    bucket = config.get(kind, {})
    if not isinstance(bucket, dict):
        return None
    value = bucket.get(name)
    if isinstance(value, dict):
        return value
    return None


def get(ctx, *positional, name=None, **kwargs):
    if name is None and positional:
        name = positional[0]

    if not isinstance(name, str) or not name:
        ctx.log("Missing input name", "ERROR")
        return None

    device = get_device_config("input", name)
    if not isinstance(device, dict):
        ctx.log("Unknown input %s" % name, "ERROR")
        return None

    driver = str(device.get("driver", "")).lower()
    provider = get_capability_provider(ctx, "input", driver)
    if not isinstance(provider, dict):
        ctx.log("No input driver %s installed" % driver, "ERROR")
        return None

    getter = provider.get("get")
    if not callable(getter):
        ctx.log("Input driver %s cannot get values" % driver, "ERROR")
        return None

    extra = []
    if len(positional) > 1:
        extra = list(positional[1:])

    return getter(ctx, name=name, config=device, positional=extra, **kwargs)


def get_module():
    return {
        "get": get
    }
