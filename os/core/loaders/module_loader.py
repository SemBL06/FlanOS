import sys
try:
    import gc
except:
    gc = None

try:
    import uos as fs
except:
    import os as fs


CUSTOM_DRIVER_PATHS = (
    "/sd/main/drivers",
    "sd/main/drivers"
)

CUSTOM_MODULE_PATHS = (
    "/sd/main/modules",
    "sd/main/modules"
)

BUILTIN_MODULE_SPECS = (
    ("display", "modules.system"),
    ("log", "modules.system"),
    ("system", "modules.system"),
    ("button", "modules.button"),
    ("controls", "modules.controls"),
    ("ui", "modules.ui_core"),
    ("config", "modules.config"),
    ("csv", "modules.csv"),
    ("data", "modules.data"),
    ("comm", "modules.comm"),
    ("input", "modules.input"),
    ("output", "modules.output"),
    ("list", "modules.list"),
    ("math", "modules.math"),
    ("string", "modules.string"),
    ("options", "modules.ui.options"),
    ("description", "modules.ui.description")
)

MANIFEST_FIELDS = {
    "name": str,
    "version": str,
    "author": str,
    "board": (str, list),
    "dependencies": list,
    "capabilities": list
}

LAZY_CUSTOM_MODULES = (
    "clock",
    "fetch",
    "keyboard",
    "mouse",
    "rfid",
    "website"
)


def file_exists(path):
    try:
        with open(path, "r"):
            return True
    except:
        return False


def dir_exists(path):
    try:
        fs.listdir(path)
        return True
    except:
        return False


def ensure_dir(path):
    try:
        fs.mkdir(path)
    except:
        pass


def ensure_dir_tree(path):
    if not isinstance(path, str) or not path:
        return

    normalized = path.replace("\\", "/")
    if normalized == "/":
        return

    parts = normalized.split("/")
    current = ""
    i = 0

    if normalized.startswith("/"):
        current = ""

    while i < len(parts):
        part = parts[i]
        i += 1
        if not part:
            continue

        if current in ("", "/"):
            current = "/" + part
        else:
            current = current + "/" + part

        ensure_dir(current)


def get_dirname(path):
    if not isinstance(path, str):
        return ""
    path = path.replace("\\", "/")
    if "/" not in path:
        return ""
    return path.rsplit("/", 1)[0]


def path_candidates(path):
    candidates = []
    if isinstance(path, str) and path:
        candidates.append(path)
        if path.startswith("/"):
            candidates.append(path[1:])
        else:
            candidates.append("/" + path)
    return candidates


def get_custom_dir(config=None, section="modules", default_paths=None):
    if default_paths is None:
        default_paths = CUSTOM_MODULE_PATHS

    path = None
    if isinstance(config, dict):
        section_config = config.get(section, {})
        if isinstance(section_config, dict):
            path = section_config.get("path")

    if isinstance(path, str) and path:
        candidates = path_candidates(path)
        existing = []
        i = 0
        while i < len(candidates):
            if dir_exists(candidates[i]):
                existing.append(candidates[i])
            i += 1

        best_path = None
        best_count = -1
        i = 0
        while i < len(existing):
            current = existing[i]
            current_count = count_module_files(current)
            if current_count > best_count:
                best_path = current
                best_count = current_count
            i += 1

        if best_path is not None:
            return best_path
        return candidates[0]

    existing = []
    i = 0
    while i < len(default_paths):
        current = default_paths[i]
        i += 1
        if dir_exists(current):
            existing.append(current)

    best_path = None
    best_count = -1
    i = 0
    while i < len(existing):
        current = existing[i]
        current_count = count_module_files(current)
        if current_count > best_count:
            best_path = current
            best_count = current_count
        i += 1

    if best_path is not None:
        return best_path

    return default_paths[0]


def get_custom_module_dir(config=None):
    return get_custom_dir(config=config, section="modules", default_paths=CUSTOM_MODULE_PATHS)


def get_custom_driver_dir(config=None):
    return get_custom_dir(config=config, section="drivers", default_paths=CUSTOM_DRIVER_PATHS)


def ensure_custom_module_dir(config=None):
    path = get_custom_module_dir(config)
    ensure_dir_tree(path)
    return path


def ensure_custom_driver_dir(config=None):
    path = get_custom_driver_dir(config)
    ensure_dir_tree(path)
    return path


def list_dir(path):
    try:
        return fs.listdir(path), None
    except Exception as e:
        return None, e


def dir_has_module_files(path):
    entries, _ = list_dir(path)
    if not isinstance(entries, list):
        return False

    i = 0
    while i < len(entries):
        name = entries[i]
        if isinstance(name, str) and name.endswith(".py") and not name.startswith("_"):
            return True
        i += 1

    return False


def count_module_files(path):
    entries, _ = list_dir(path)
    if not isinstance(entries, list):
        return 0

    total = 0
    i = 0
    while i < len(entries):
        name = entries[i]
        i += 1
        if isinstance(name, str) and name.endswith(".py") and not name.startswith("_"):
            total += 1

    return total


def get_custom_settings(config=None, section="modules", default_paths=None):
    defaults = {
        "enabled": True,
        "allow_override": False,
        "path": get_custom_dir(config, section=section, default_paths=default_paths),
        "board": "generic"
    }

    if not isinstance(config, dict):
        return defaults

    section_config = config.get(section, {})
    if not isinstance(section_config, dict):
        return defaults

    result = {}
    for key in defaults:
        result[key] = section_config.get(key, defaults[key])
    return result


def get_module_settings(config=None):
    return get_custom_settings(config=config, section="modules", default_paths=CUSTOM_MODULE_PATHS)


def get_driver_settings(config=None):
    return get_custom_settings(config=config, section="drivers", default_paths=CUSTOM_DRIVER_PATHS)


def is_valid_module_name(name):
    if not isinstance(name, str) or not name:
        return False

    i = 0
    while i < len(name):
        char = name[i]
        is_letter = ("a" <= char <= "z") or ("A" <= char <= "Z")
        is_digit = "0" <= char <= "9"
        if not (is_letter or is_digit or char == "_"):
            return False
        i += 1

    return True


def get_context_manifest_store(ctx):
    store = ctx.vars.get("_module_manifests")
    if not isinstance(store, dict):
        store = {}
        ctx.vars["_module_manifests"] = store
    return store


def get_context_source_store(ctx):
    store = ctx.vars.get("_module_sources")
    if not isinstance(store, dict):
        store = {}
        ctx.vars["_module_sources"] = store
    return store


def get_context_provider_store(ctx):
    store = ctx.vars.get("_providers")
    if not isinstance(store, dict):
        store = {}
        ctx.vars["_providers"] = store
    return store


def get_context_capability_provider_store(ctx):
    store = ctx.vars.get("_capability_providers")
    if not isinstance(store, dict):
        store = {}
        ctx.vars["_capability_providers"] = store
    return store


def get_context_lazy_store(ctx):
    store = ctx.vars.get("_lazy_modules")
    if not isinstance(store, dict):
        store = {}
        ctx.vars["_lazy_modules"] = store
    return store


def normalize_manifest(name, manifest, source, path):
    result = {
        "name": name,
        "version": "",
        "author": "",
        "board": "any",
        "dependencies": [],
        "capabilities": [],
        "source": source,
        "path": path
    }

    if isinstance(manifest, dict):
        for key in MANIFEST_FIELDS:
            if key in manifest:
                result[key] = manifest[key]

    return result


def validate_manifest(ctx, manifest):
    for key in MANIFEST_FIELDS:
        value = manifest.get(key)
        expected = MANIFEST_FIELDS[key]
        if value == "":
            continue
        if key in ("dependencies", "capabilities") and value == []:
            continue
        if not isinstance(value, expected):
            ctx.log("Invalid manifest field %s for module %s" % (key, manifest.get("name", "")), "ERROR")
            return False

    return True


def board_matches(manifest, settings):
    board = manifest.get("board", "any")
    target = settings.get("board", "generic")

    if isinstance(board, list):
        return target in board or "any" in board

    return board in ("", "any", target)


def dependencies_met(manifest, executor):
    dependencies = manifest.get("dependencies", [])
    i = 0
    while i < len(dependencies):
        if dependencies[i] not in executor.modules:
            return False
        i += 1
    return True


def validate_module_dict(ctx, name, module_dict):
    if not isinstance(module_dict, dict):
        ctx.log("Module %s did not return a dict" % name, "ERROR")
        return False

    for key in module_dict:
        if not callable(module_dict[key]):
            ctx.log("Module %s has non-callable action %s" % (name, key), "ERROR")
            return False

    return True


def register_module(executor, ctx, name, module_dict, manifest, source, allow_override=False):
    if not is_valid_module_name(name):
        ctx.log("Invalid module name: %s" % name, "ERROR")
        return False

    if name in executor.modules and not allow_override:
        ctx.log("Skipping module override for %s" % name, "WARN")
        return False

    executor.register_module(name, module_dict)
    manifest_store = get_context_manifest_store(ctx)
    source_store = get_context_source_store(ctx)
    manifest_store[name] = manifest
    source_store[name] = source
    return True


def register_lazy_module(ctx, name, path, source="custom"):
    store = get_context_lazy_store(ctx)
    store[name] = {
        "path": path,
        "source": source
    }

    manifest_store = get_context_manifest_store(ctx)
    source_store = get_context_source_store(ctx)
    manifest_store[name] = normalize_manifest(name, {}, source, path)
    source_store[name] = path
    return True


def import_builtin_module(path):
    module = __import__(path, None, None, ["get_module"])
    return module


def load_builtin_modules(executor, ctx):
    i = 0
    while i < len(BUILTIN_MODULE_SPECS):
        name, path = BUILTIN_MODULE_SPECS[i]
        i += 1

        module_ref = import_builtin_module(path)
        module_dict = module_ref.get_module()
        manifest = normalize_manifest(name, {}, "builtin", path)
        register_module(executor, ctx, name, module_dict, manifest, "builtin:%s" % path, allow_override=True)


def read_custom_namespace(path):
    namespace = {
        "__file__": path,
        "__name__": "custom_module_%s" % path.replace("\\", "_").replace("/", "_")
    }

    with open(path, "r") as f:
        source = f.read()

    exec(source, namespace)
    return namespace


def import_custom_namespace(module_name):
    module = __import__(module_name, None, None, ["get_module"])
    namespace = module.__dict__
    if "__name__" not in namespace:
        namespace["__name__"] = module_name
    return namespace


def get_manifest_from_namespace(namespace):
    getter = namespace.get("get_manifest")
    if callable(getter):
        return getter()

    manifest = namespace.get("MODULE_MANIFEST")
    if isinstance(manifest, dict):
        return manifest

    return {}


def get_config_defaults_from_namespace(namespace):
    getter = namespace.get("get_config_defaults")
    if callable(getter):
        result = getter()
        if isinstance(result, dict):
            return result

    defaults = namespace.get("CONFIG_DEFAULTS")
    if isinstance(defaults, dict):
        return defaults

    return {}


def run_autoconfigure(namespace, ctx, config):
    hook = namespace.get("autoconfigure")
    if callable(hook):
        try:
            return hook(ctx, config)
        except Exception as e:
            ctx.log("Autoconfigure failed: %s" % e, "ERROR")
    return config


def register_provider(ctx, kind, provider, source_name):
    if not isinstance(provider, dict):
        return False

    if kind == "display":
        try:
            from core.storage.config import ensure_main_config
            config = ensure_main_config()
            display = config.get("display", {})
            buttons = config.get("buttons", {})
            if isinstance(display, dict):
                matched_index = -1
                matched_entry = None
                index = 0
                for key in display:
                    entry = display.get(key)
                    if not isinstance(entry, dict):
                        continue
                    wanted = str(entry.get("driver", "")).lower()
                    if wanted == str(source_name).lower():
                        matched_index = index
                        matched_entry = entry
                        break
                    index += 1

                if matched_index == -1:
                    return False

                if isinstance(matched_entry, dict) and isinstance(buttons, dict):
                    display_pins = []
                    for pin_key in ("sda", "scl"):
                        try:
                            display_pins.append(int(matched_entry.get(pin_key)))
                        except:
                            pass

                    button_pins = []
                    for pin_key in ("up", "down", "left", "right"):
                        try:
                            button_pins.append(int(buttons.get(pin_key)))
                        except:
                            pass

                    overlap = []
                    i = 0
                    while i < len(display_pins):
                        pin = display_pins[i]
                        i += 1
                        if pin in button_pins and pin not in overlap:
                            overlap.append(pin)

                    if overlap:
                        ctx.log(
                            "Skipped display provider %s due to button pin conflict on GP%s" % (
                                source_name,
                                ",GP".join([str(pin) for pin in overlap])
                            ),
                            "WARN"
                        )
                        return False

                probe = provider.get("probe")
                if callable(probe):
                    try:
                        if not probe(ctx):
                            ctx.log("Display provider %s not detected" % source_name, "WARN")
                            return False
                    except Exception as e:
                        ctx.log("Display provider %s probe failed: %s" % (source_name, e), "WARN")
                        return False

                current_index = ctx.vars.get("_display_provider_index")
                if isinstance(current_index, int) and current_index <= matched_index:
                    return False

                ctx.vars["_display_provider_index"] = matched_index
        except:
            pass

    store = get_context_provider_store(ctx)
    store[kind] = provider
    ctx.vars["_%s_provider_name" % kind] = source_name
    ctx.log("Registered %s provider from %s" % (kind, source_name))
    return True


def register_capability_provider(ctx, kind, provider, source_name):
    if not isinstance(provider, dict):
        return False

    store = get_context_capability_provider_store(ctx)
    bucket = store.get(kind)
    if not isinstance(bucket, dict):
        bucket = {}
        store[kind] = bucket

    bucket[source_name] = provider
    ctx.log("Registered %s capability provider from %s" % (kind, source_name))
    return True


def get_display_provider_from_namespace(namespace, ctx):
    getter = namespace.get("get_display_provider")
    if callable(getter):
        return getter(ctx)

    provider = namespace.get("DISPLAY_PROVIDER")
    if isinstance(provider, dict):
        return provider

    return None


def get_capability_provider_from_namespace(namespace, ctx, kind):
    getter = namespace.get("get_%s_provider" % kind)
    if callable(getter):
        return getter(ctx)

    key = "%s_PROVIDER" % kind.upper()
    provider = namespace.get(key)
    if isinstance(provider, dict):
        return provider

    return None


def is_provider_only_manifest(manifest):
    capabilities = manifest.get("capabilities", [])
    if not isinstance(capabilities, list):
        return False

    i = 0
    while i < len(capabilities):
        capability = capabilities[i]
        i += 1
        if isinstance(capability, str) and capability.endswith("-provider"):
            return True

    return False


def register_namespace_providers(ctx, namespace, module_name):
    registered = False

    provider = get_display_provider_from_namespace(namespace, ctx)
    if provider is not None:
        if register_provider(ctx, "display", provider, module_name):
            registered = True

    kind = "comm"
    provider = get_capability_provider_from_namespace(namespace, ctx, kind)
    if provider is not None:
        if register_capability_provider(ctx, kind, provider, module_name):
            registered = True

    kind = "input"
    provider = get_capability_provider_from_namespace(namespace, ctx, kind)
    if provider is not None:
        if register_capability_provider(ctx, kind, provider, module_name):
            registered = True

    kind = "output"
    provider = get_capability_provider_from_namespace(namespace, ctx, kind)
    if provider is not None:
        if register_capability_provider(ctx, kind, provider, module_name):
            registered = True

    return registered


def load_lazy_module(executor, ctx, name):
    store = get_context_lazy_store(ctx)
    entry = store.get(name)
    if not isinstance(entry, dict):
        return False

    path = entry.get("path")
    if not isinstance(path, str) or not path:
        return False

    try:
        namespace = import_custom_namespace(name)
    except Exception:
        try:
            namespace = read_custom_namespace(path)
        except Exception as e:
            ctx.log("Failed to load lazy module %s: %s" % (name, e), "ERROR")
            return False

    get_module = namespace.get("get_module")
    if not callable(get_module):
        ctx.log("Custom module %s is missing get_module()" % name, "ERROR")
        return False

    manifest = normalize_manifest(name, get_manifest_from_namespace(namespace), "custom", path)
    module_name = manifest.get("name", name)

    try:
        module_dict = get_module()
    except Exception as e:
        ctx.log("Custom module %s get_module failed: %s" % (module_name, e), "ERROR")
        return False

    if not validate_module_dict(ctx, module_name, module_dict):
        return False

    if not register_module(executor, ctx, module_name, module_dict, manifest, path, allow_override=False):
        return False

    register_namespace_providers(ctx, namespace, module_name)
    try:
        del store[name]
    except:
        pass
    if gc is not None:
        try:
            gc.collect()
        except:
            pass
    ctx.log("Loaded lazy module %s" % module_name)
    return True


def load_custom_collection(executor, ctx, config=None, section="modules", default_paths=None, label="module"):
    from core.storage.config import ensure_config_defaults, save_main_config

    settings = get_custom_settings(config=config, section=section, default_paths=default_paths)
    if not settings.get("enabled", True):
        ctx.log("Custom %ss disabled" % label, "WARN")
        return []

    module_dir = get_custom_dir(config=config, section=section, default_paths=default_paths)
    ensure_dir_tree(module_dir)
    loaded = []
    ctx.log("Custom %s dir: %s" % (label, module_dir))
    if module_dir and module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    entries, error = list_dir(module_dir)
    if entries is None:
        ctx.log("Unable to list custom %s dir: %s (%s)" % (label, module_dir, error), "ERROR")
        sd_entries, _ = list_dir("/sd")
        main_entries, _ = list_dir("/sd/main")
        if sd_entries is not None:
            ctx.log("Entries in /sd: %s" % ", ".join(sd_entries))
        if main_entries is not None:
            ctx.log("Entries in /sd/main: %s" % ", ".join(main_entries))
        return loaded

    ctx.log("Custom %s entries: %s" % (label, ", ".join(entries)))

    i = 0
    while i < len(entries):
        name = entries[i]
        i += 1

        if not name.endswith(".py") or name.startswith("_"):
            continue

        path = module_dir + "/" + name if not module_dir.endswith("/") else module_dir + name
        module_name = name[:-3]

        if section == "modules" and module_name in LAZY_CUSTOM_MODULES:
            register_lazy_module(ctx, module_name, path)
            loaded.append(module_name)
            ctx.log("Registered lazy module %s" % module_name)
            continue

        ctx.log("Loading custom module file %s" % path)

        try:
            if section == "drivers":
                namespace = import_custom_namespace(module_name)
            else:
                namespace = read_custom_namespace(path)
        except Exception as e:
            ctx.log("Failed to load custom module %s: %s" % (name, e), "ERROR")
            continue

        manifest = normalize_manifest(module_name, get_manifest_from_namespace(namespace), "custom", path)
        module_name = manifest.get("name", module_name)
        ctx.log("Custom module manifest name: %s" % module_name)

        defaults = get_config_defaults_from_namespace(namespace)
        if defaults:
            config = ensure_config_defaults(defaults)
            settings = get_custom_settings(config=config, section=section, default_paths=default_paths)

        updated = run_autoconfigure(namespace, ctx, config)
        if isinstance(updated, dict):
            config = updated
            save_main_config(config)
            settings = get_custom_settings(config=config, section=section, default_paths=default_paths)

        if not validate_manifest(ctx, manifest):
            continue

        if not board_matches(manifest, settings):
            ctx.log("Skipping module %s due to board mismatch" % module_name, "WARN")
            continue

        if not dependencies_met(manifest, executor):
            ctx.log("Skipping module %s due to missing dependencies" % module_name, "WARN")
            continue

        provider_only = is_provider_only_manifest(manifest)
        registered = False

        if provider_only:
            manifest_store = get_context_manifest_store(ctx)
            source_store = get_context_source_store(ctx)
            manifest_store[module_name] = manifest
            source_store[module_name] = path
            registered = True
        else:
            get_module = namespace.get("get_module")
            if not callable(get_module):
                ctx.log("Custom module %s is missing get_module()" % name, "ERROR")
                continue

            try:
                module_dict = get_module()
            except Exception as e:
                ctx.log("Custom module %s get_module failed: %s" % (module_name, e), "ERROR")
                continue

            if not validate_module_dict(ctx, module_name, module_dict):
                continue

            registered = register_module(
                executor,
                ctx,
                module_name,
                module_dict,
                manifest,
                path,
                allow_override=bool(settings.get("allow_override", False))
            )

        if registered:
            provider_registered = True
            if provider_only:
                provider_registered = register_namespace_providers(ctx, namespace, module_name)
            else:
                register_namespace_providers(ctx, namespace, module_name)

            if provider_only and not provider_registered:
                manifest_store = get_context_manifest_store(ctx)
                source_store = get_context_source_store(ctx)
                try:
                    del manifest_store[module_name]
                except:
                    pass
                try:
                    del source_store[module_name]
                except:
                    pass
                if section == "drivers":
                    try:
                        del sys.modules[name[:-3]]
                    except:
                        pass
                ctx.log("Skipped custom provider %s" % module_name, "WARN")
            else:
                loaded.append(module_name)
                if provider_only:
                    ctx.log("Loaded custom provider %s" % module_name)
                else:
                    ctx.log("Loaded custom module %s" % module_name)

        namespace = None
        if gc is not None:
            try:
                gc.collect()
            except:
                pass

    return loaded


def load_custom_drivers(executor, ctx, config=None):
    return load_custom_collection(
        executor,
        ctx,
        config=config,
        section="drivers",
        default_paths=CUSTOM_DRIVER_PATHS,
        label="driver"
    )


def load_custom_modules(executor, ctx, config=None):
    return load_custom_collection(
        executor,
        ctx,
        config=config,
        section="modules",
        default_paths=CUSTOM_MODULE_PATHS,
        label="module"
    )
