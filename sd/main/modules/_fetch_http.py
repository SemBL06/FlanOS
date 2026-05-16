try:
    import urequests as requests_lib
except:
    try:
        import requests as requests_lib
    except:
        requests_lib = None

try:
    import urllib.request as urllib_request
except:
    urllib_request = None

try:
    import usocket as socket_lib
except:
    try:
        import socket as socket_lib
    except:
        socket_lib = None

try:
    import ujson as json_lib
except:
    import json as json_lib

from core.storage.config import ensure_main_config
from core.utils.args import pick_arg
from core.utils.paths import get_path_value

DEFAULT_MAX_BYTES = 2048
DEFAULT_TIMEOUT_MS = 5000


def _to_int(value, default):
    try:
        return int(value)
    except:
        return default


def _get_header(headers, name):
    if not isinstance(headers, dict):
        return None

    wanted = str(name).lower()
    for key in headers:
        if str(key).lower() == wanted:
            return headers[key]
    return None


def _close_response(response):
    try:
        response.close()
    except:
        pass


def _read_limited(response, max_bytes):
    max_bytes = _to_int(max_bytes, DEFAULT_MAX_BYTES)
    if max_bytes < 128:
        max_bytes = 128

    headers = getattr(response, "headers", {})
    content_length = _get_header(headers, "Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                raise ValueError("Response exceeds max_bytes")
        except:
            pass

    raw = getattr(response, "raw", None)
    if raw is not None and hasattr(raw, "read"):
        body = raw.read(max_bytes + 1)
        if body is None:
            body = b""
        if len(body) > max_bytes:
            raise ValueError("Response exceeds max_bytes")
        return body

    body = getattr(response, "content", b"")
    if body is None:
        body = b""
    if isinstance(body, str):
        body = body.encode()
    if len(body) > max_bytes:
        raise ValueError("Response exceeds max_bytes")
    return body


def _decode_json(body):
    if isinstance(body, bytes):
        body = body.decode()
    return json_lib.loads(body)


def _set_timeout(timeout_ms):
    if socket_lib is None or not hasattr(socket_lib, "setdefaulttimeout"):
        return None
    seconds = max(1, _to_int(timeout_ms, DEFAULT_TIMEOUT_MS)) / 1000
    try:
        socket_lib.setdefaulttimeout(seconds)
        return True
    except:
        return None


def _store_last_fetch(ctx, url, method, response, raw, parsed):
    headers = getattr(response, "headers", {})
    if not isinstance(headers, dict):
        try:
            headers = dict(headers)
        except:
            headers = {}

    ctx.vars["_fetch_last"] = {
        "url": url,
        "method": method,
        "status": getattr(response, "status_code", 200),
        "headers": headers,
        "bytes": len(raw),
        "body": parsed
    }


def _extract_path(value, path):
    if not isinstance(path, str) or not path:
        return value
    return get_path_value(value, path)


def _request_json(method, ctx, url, value=None, max_bytes=None, timeout=None, path=None):
    if requests_lib is None and urllib_request is None:
        ctx.log("HTTP unavailable", "ERROR")
        return None

    if not isinstance(url, str) or not url:
        ctx.log("Missing url", "ERROR")
        return None

    max_bytes = _to_int(max_bytes, DEFAULT_MAX_BYTES)
    timeout = _to_int(timeout, DEFAULT_TIMEOUT_MS)
    headers = {"Accept": "application/json"}
    body = None
    timeout_set = _set_timeout(timeout)

    if value is not None:
        resolved = ctx.executor.resolve(value)
        if isinstance(resolved, (dict, list)):
            body = json_lib.dumps(resolved)
            headers["Content-Type"] = "application/json"
        else:
            body = str(resolved)
            headers["Content-Type"] = "application/json"

    response = None
    try:
        if requests_lib is not None and method == "GET":
            response = requests_lib.get(url, headers=headers)
        elif requests_lib is not None:
            response = requests_lib.post(url, data=body, headers=headers)
        else:
            req = urllib_request.Request(url, headers=headers, method=method)
            data = None if body is None else body.encode()
            raw_response = urllib_request.urlopen(req, data=data)

            class SimpleResponse:
                def __init__(self, inner):
                    self.raw = inner
                    self.headers = dict(inner.getheaders())
                    self.status_code = getattr(inner, "status", 200)

                def close(self):
                    self.raw.close()

            response = SimpleResponse(raw_response)

        raw = _read_limited(response, max_bytes)
        parsed = _decode_json(raw)
        _store_last_fetch(ctx, url, method, response, raw, parsed)
        return _extract_path(parsed, path)
    except Exception as e:
        ctx.log("Fetch %s failed: %s" % (method.lower(), e), "ERROR")
        return None
    finally:
        if timeout_set:
            try:
                socket_lib.setdefaulttimeout(None)
            except:
                pass
        if response is not None:
            _close_response(response)


def _parse_version(value):
    parts = str(value or "").split(".")
    result = []
    i = 0
    while i < len(parts):
        piece = parts[i]
        i += 1
        digits = ""
        j = 0
        while j < len(piece):
            char = piece[j]
            if "0" <= char <= "9":
                digits += char
            else:
                break
            j += 1
        if digits == "":
            result.append(0)
        else:
            result.append(int(digits))
    return result


def _version_newer(remote, local):
    remote_parts = _parse_version(remote)
    local_parts = _parse_version(local)
    length = len(remote_parts)
    if len(local_parts) > length:
        length = len(local_parts)

    i = 0
    while i < length:
        remote_value = remote_parts[i] if i < len(remote_parts) else 0
        local_value = local_parts[i] if i < len(local_parts) else 0
        if remote_value > local_value:
            return True
        if remote_value < local_value:
            return False
        i += 1

    return False


def _normalize_update_payload(payload):
    modules = []

    if isinstance(payload, dict):
        current = payload.get("modules")
        if isinstance(current, dict):
            for name in current:
                item = current[name]
                if isinstance(item, dict):
                    row = {"name": name}
                    for key in item:
                        row[key] = item[key]
                    modules.append(row)
            return modules

        if isinstance(current, list):
            return current

        return modules

    if isinstance(payload, list):
        return payload

    return modules


def get_updates(ctx, *positional, url=None, max_bytes=None, timeout=None):
    if url is None and len(positional) > 1:
        url = positional[1]

    if url is None:
        config = ensure_main_config()
        fetch_config = config.get("fetch", {})
        if isinstance(fetch_config, dict):
            url = fetch_config.get("updates_url")
        if url is None:
            modules_config = config.get("modules", {})
            if isinstance(modules_config, dict):
                url = modules_config.get("update_url")

    if not isinstance(url, str) or not url:
        ctx.log("Missing fetch updates url", "ERROR")
        return []

    payload = _request_json("GET", ctx, url, max_bytes=max_bytes, timeout=timeout)
    available = _normalize_update_payload(payload)
    manifests = ctx.vars.get("_module_manifests", {})
    if not isinstance(manifests, dict):
        manifests = {}

    updates = []
    i = 0
    while i < len(available):
        item = available[i]
        i += 1
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        version = item.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue

        current = manifests.get(name, {})
        current_version = ""
        if isinstance(current, dict):
            current_version = current.get("version", "")

        if _version_newer(version, current_version):
            updates.append({
                "name": name,
                "current": current_version,
                "version": version,
                "url": item.get("url"),
                "source": item.get("source")
            })

    ctx.vars["_fetch_updates"] = updates
    return updates


def get(ctx, *positional, url=None, max_bytes=None, timeout=None, path=None):
    first = positional[0] if positional else None
    if first == "updates":
        return get_updates(ctx, *positional, url=url, max_bytes=max_bytes, timeout=timeout)

    url = pick_arg(positional, 0, url)
    max_bytes = pick_arg(positional, 1, max_bytes, DEFAULT_MAX_BYTES)
    timeout = pick_arg(positional, 2, timeout, DEFAULT_TIMEOUT_MS)
    return _request_json("GET", ctx, url, max_bytes=max_bytes, timeout=timeout, path=path)


def post(ctx, *positional, url=None, value=None, max_bytes=None, timeout=None, path=None):
    url = pick_arg(positional, 0, url)
    value = pick_arg(positional, 1, value)
    max_bytes = pick_arg(positional, 2, max_bytes, DEFAULT_MAX_BYTES)
    timeout = pick_arg(positional, 3, timeout, DEFAULT_TIMEOUT_MS)
    return _request_json("POST", ctx, url, value=value, max_bytes=max_bytes, timeout=timeout, path=path)


def response(ctx, *positional, field=None):
    if positional:
        field = positional[0]

    data = ctx.vars.get("_fetch_last", {})
    if not isinstance(data, dict):
        data = {}

    if field is None:
        return data

    return data.get(str(field).lower())


def status(ctx, *positional, type=None):
    mode = type
    if mode is None and positional:
        mode = positional[0]

    data = response(ctx)
    code = data.get("status")
    if mode is None:
        return code

    mode = str(mode).lower()
    if mode == "ok":
        return isinstance(code, int) and code >= 200 and code < 300
    if mode == "redirect":
        return isinstance(code, int) and code >= 300 and code < 400
    if mode == "client_error":
        return isinstance(code, int) and code >= 400 and code < 500
    if mode == "server_error":
        return isinstance(code, int) and code >= 500

    return code


def headers(ctx):
    data = response(ctx)
    headers = data.get("headers", {})
    if isinstance(headers, dict):
        return headers
    return {}


def header(ctx, *positional, name=None):
    name = pick_arg(positional, 0, name)
    if not isinstance(name, str) or not name:
        ctx.log("Missing header name", "ERROR")
        return None
    return _get_header(headers(ctx), name)
