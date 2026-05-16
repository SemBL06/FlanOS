def ping(ctx, text="pong"):
    return text


def get(ctx, field=None):
    if field == "status":
        return "ready"

    return {
        "status": "ready",
        "kind": "demo"
    }


def get_module():
    return {
        "ping": ping,
        "get": get
    }


def get_manifest():
    return {
        "name": "demo",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["example", "custom-module"]
    }
