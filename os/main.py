import os
import sys
try:
    import gc
except:
    gc = None

if "/os" not in sys.path:
    sys.path.insert(0, "/os")
if "os" not in sys.path:
    sys.path.insert(0, "os")

from core.storage.config import ensure_main_config, get_config_path
from core.storage.sdcard import mount_boot_sd
from core.context import Context
from core.executor import Executor
from core.loaders.module_loader import (
    ensure_custom_driver_dir,
    ensure_custom_module_dir,
    load_builtin_modules,
    load_custom_drivers,
    load_custom_modules
)
BOOT_DIR = "/sd/main"
BOOT_SCRIPT = BOOT_DIR + "/main.fl"
BOOT_CONFIG = get_config_path()
CUSTOM_DRIVER_DIR = "/sd/main/drivers"
CUSTOM_MODULE_DIR = "/sd/main/modules"
EXAMPLE_CUSTOM_MODULE = CUSTOM_MODULE_DIR + "/demo.py"

DEFAULT_BOOT_SCRIPT = """display print text="Flan OS" x=0 y=0
set scripts to (system scripts)
if display available
    controls reset
    set launch to ""
    set selected to (ui options list=scripts field=name selected=0 right=continue)
    while on
        set selected to (ui options right=continue)
        if (ui action) == "select"
            set launch to selected
            log info "Launching {launch.path}"
            stop
        end
        if (controls pressed state=right)
            set launch to selected
            log info "Launching {launch.path}"
            stop
        end
        if (controls pressed state=left)
            set launch to selected
            log info "Launching {launch.path}"
            stop
        end
        system sleep 80
    end
    if launch
        system run launch
    end
else
    log warn "No display available; boot menu skipped"
end
"""

DEFAULT_CUSTOM_MODULE = """def ping(ctx, text="pong"):
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
"""

def ensure_dir(path):
    try:
        os.mkdir(path)
    except:
        pass


def file_exists(path):
    try:
        with open(path, "r"):
            return True
    except:
        return False


def ensure_file(path, default_content):
    if file_exists(path):
        return

    with open(path, "w") as f:
        f.write(default_content)


def tune_gc():
    if gc is None or not hasattr(gc, "collect"):
        return

    try:
        gc.collect()
    except:
        pass

    if hasattr(gc, "threshold") and hasattr(gc, "mem_free") and hasattr(gc, "mem_alloc"):
        try:
            gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
        except:
            pass

# Setup
ctx = Context()
executor = Executor(ctx)
ctx.executor = executor  # needed for events

mount_boot_sd(ctx)
ensure_dir(BOOT_DIR)
ensure_file(BOOT_SCRIPT, DEFAULT_BOOT_SCRIPT)
config = ensure_main_config()
drivers_config = config.get("drivers")
if not isinstance(drivers_config, dict):
    drivers_config = {}
    config["drivers"] = drivers_config
drivers_config["path"] = CUSTOM_DRIVER_DIR
modules_config = config.get("modules")
if not isinstance(modules_config, dict):
    modules_config = {}
    config["modules"] = modules_config
modules_config["path"] = CUSTOM_MODULE_DIR
ensure_custom_driver_dir(config)
ensure_custom_module_dir(config)
ensure_file(EXAMPLE_CUSTOM_MODULE, DEFAULT_CUSTOM_MODULE)
tune_gc()
load_builtin_modules(executor, ctx)
loaded_drivers = load_custom_drivers(executor, ctx, config)
ctx.log("Loaded custom drivers: %s" % ", ".join(loaded_drivers))
tune_gc()
loaded_custom = load_custom_modules(executor, ctx, config)
ctx.log("Loaded custom modules: %s" % ", ".join(loaded_custom))
tune_gc()
boot_target = BOOT_SCRIPT

try:
    # Boot script
    executor.execute_script(boot_target)

    # Trigger test event
    executor.trigger_event("system", "start")
except Exception as e:
    ctx.log_exception(e, "Boot failure for %s" % boot_target)
