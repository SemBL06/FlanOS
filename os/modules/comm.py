def get_capability_provider(ctx, kind, name):
    store = ctx.vars.get("_capability_providers", {})
    if not isinstance(store, dict):
        return None

    bucket = store.get(kind, {})
    if not isinstance(bucket, dict):
        return None

    return bucket.get(name)


def list_providers(ctx):
    store = ctx.vars.get("_capability_providers", {})
    if not isinstance(store, dict):
        return []

    bucket = store.get("comm", {})
    if not isinstance(bucket, dict):
        return []

    names = []
    for name in bucket:
        names.append(name)
    return names


def scan(ctx, *positional, provider=None, type=None, **kwargs):
    if provider is None:
        provider = type
    if provider is None and positional:
        provider = positional[0]

    provider = str(provider or "").lower()
    ref = get_capability_provider(ctx, "comm", provider)
    if not isinstance(ref, dict):
        ctx.log("Unknown comm provider %s" % provider, "ERROR")
        return []

    func = ref.get("scan")
    if not callable(func):
        ctx.log("Comm provider %s cannot scan" % provider, "ERROR")
        return []

    return func(ctx, **kwargs)


def get(ctx, *positional, provider=None, value=None, **kwargs):
    if provider is None and positional:
        provider = positional[0]
    if value is None and len(positional) > 1:
        value = positional[1]

    provider = str(provider or "").lower()
    ref = get_capability_provider(ctx, "comm", provider)
    if not isinstance(ref, dict):
        ctx.log("Unknown comm provider %s" % provider, "ERROR")
        return None

    func = ref.get("get")
    if not callable(func):
        ctx.log("Comm provider %s cannot get values" % provider, "ERROR")
        return None

    if value is None:
        ctx.log("Missing comm value", "ERROR")
        return None

    return func(ctx, value, **kwargs)


def get_module():
    return {
        "scan": scan,
        "get": get,
        "list": list_providers
    }
