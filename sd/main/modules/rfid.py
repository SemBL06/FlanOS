def contact(ctx):
    ctx.log("RFID contact detected")
    ctx.executor.trigger_event("RFID", "contact")


def get_module():
    return {
        "contact": contact
    }


def get_manifest():
    return {
        "name": "rfid",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["rfid", "extension-module"]
    }
