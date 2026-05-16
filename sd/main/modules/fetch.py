try:
    import usocket as socket_lib
except:
    try:
        import socket as socket_lib
    except:
        socket_lib = None

try:
    import _thread as thread_lib
except:
    try:
        import threading as thread_lib
    except:
        thread_lib = None

try:
    import ujson as json_lib
except:
    import json as json_lib

try:
    import network as network_lib
except:
    network_lib = None
from _wifi_runtime import ensure_wifi, get_ip_address

LISTENER_STATE = {
    "running": False,
    "port": None,
    "path": "/",
    "socket": None,
    "ctx": None,
    "last": None,
    "ip": None
}

_HTTP_HELPER = None


def _load_http_helper():
    global _HTTP_HELPER
    if _HTTP_HELPER is not None:
        return _HTTP_HELPER
    try:
        import gc
        gc.collect()
    except:
        pass
    import _fetch_http as helper
    _HTTP_HELPER = helper
    return helper


def _to_int(value, default):
    try:
        return int(value)
    except:
        return default


def _decode_text(value):
    try:
        return value.decode()
    except:
        try:
            return value.decode("utf-8", "ignore")
        except:
            return str(value)


def _read_request(client):
    raw = b""
    while b"\r\n\r\n" not in raw:
        chunk = client.recv(512)
        if not chunk:
            break
        raw += chunk

    if not raw:
        return None, None, {}, b""

    header_end = raw.find(b"\r\n\r\n")
    if header_end == -1:
        return None, None, {}, b""

    header_text = _decode_text(raw[:header_end])
    body = raw[header_end + 4:]
    lines = header_text.split("\r\n")
    if not lines:
        return None, None, {}, b""

    request_line = lines[0].split(" ")
    if len(request_line) < 2:
        return None, None, {}, b""

    method = request_line[0]
    path = request_line[1]
    headers = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        i += 1

    try:
        content_length = int(headers.get("content-length", "0"))
    except:
        content_length = 0

    while len(body) < content_length:
        chunk = client.recv(512)
        if not chunk:
            break
        body += chunk

    return method, path, headers, body


def _send_response(client, status, body, content_type="application/json"):
    if isinstance(body, str):
        body = body.encode()
    response = "HTTP/1.1 %s\r\n" % status
    response += "Content-Type: %s\r\n" % content_type
    response += "Content-Length: %s\r\n" % len(body)
    response += "Connection: close\r\n\r\n"
    client.send(response.encode() + body)


def _extract_path(value, path):
    if not isinstance(path, str) or not path:
        return value
    helper = _load_http_helper()
    return helper._extract_path(value, path)


def _store_listener_payload(ctx, path, headers, raw_body, parsed):
    data = {
        "url": path,
        "method": "POST",
        "status": 200,
        "headers": headers,
        "bytes": len(raw_body),
        "body": parsed
    }
    LISTENER_STATE["last"] = data
    if ctx is not None:
        ctx.vars["_fetch_last"] = data
        ctx.vars["_fetch_listen_last"] = parsed


def _handle_listener_client(client):
    method, path, headers, body = _read_request(client)
    ctx = LISTENER_STATE.get("ctx")
    wanted = LISTENER_STATE.get("path", "/")

    if method != "POST" or path != wanted:
        _send_response(client, "404 Not Found", '{"status":"not_found"}')
        return

    try:
        parsed = json_lib.loads(body)
    except Exception as e:
        if ctx is not None:
            ctx.log("Fetch listen parse failed: %s" % e, "ERROR")
        _send_response(client, "400 Bad Request", '{"status":"invalid_json"}')
        return

    _store_listener_payload(ctx, path, headers, body, parsed)
    _send_response(client, "200 OK", '{"status":"success"}')


def _listener_loop():
    sock = LISTENER_STATE.get("socket")
    while LISTENER_STATE.get("running"):
        try:
            client, _addr = sock.accept()
        except Exception:
            continue
        try:
            _handle_listener_client(client)
        except Exception as e:
            ctx = LISTENER_STATE.get("ctx")
            if ctx is not None:
                ctx.log("Fetch listen failed: %s" % e, "ERROR")
        finally:
            try:
                client.close()
            except:
                pass


def _start_listener_thread():
    if thread_lib is None:
        return False
    if hasattr(thread_lib, "start_new_thread"):
        thread_lib.start_new_thread(_listener_loop, ())
        return True
    thread = thread_lib.Thread(target=_listener_loop)
    thread.daemon = True
    thread.start()
    return True


def _get_local_ip():
    if network_lib is None:
        return None
    ip = get_ip_address(default_value=None)
    return ip


def listen(ctx, *positional, port=None, path=None, field=None):
    mode = None
    if positional:
        mode = str(positional[0]).lower()

    if mode == "status":
        info = {
            "state": "online" if LISTENER_STATE.get("running") else "offline",
            "port": LISTENER_STATE.get("port"),
            "path": LISTENER_STATE.get("path"),
            "ip": LISTENER_STATE.get("ip")
        }
        if field:
            return info.get(str(field).lower())
        return info.get("state")

    if mode == "stop":
        LISTENER_STATE["running"] = False
        sock = LISTENER_STATE.get("socket")
        try:
            sock.close()
        except:
            pass
        LISTENER_STATE["socket"] = None
        LISTENER_STATE["ip"] = None
        return "offline"

    if mode in ("get", "last", "body"):
        last = LISTENER_STATE.get("last")
        if not isinstance(last, dict):
            return None
        if field:
            return _extract_path(last.get("body"), field)
        return last.get("body")

    if socket_lib is None:
        ctx.log("Fetch listen unavailable", "ERROR")
        return "offline"

    if LISTENER_STATE.get("running"):
        return "online"

    ensure_wifi(ctx, label="fetch")

    port = _to_int(port, 8080)
    if path is None:
        path = "/"
    if not str(path).startswith("/"):
        path = "/" + str(path)

    try:
        sock = socket_lib.socket()
        sock.setsockopt(socket_lib.SOL_SOCKET, socket_lib.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.listen(1)
        try:
            sock.settimeout(1)
        except:
            pass
    except Exception as e:
        ctx.log("Fetch listen start failed: %s" % e, "ERROR")
        try:
            sock.close()
        except:
            pass
        return "offline"

    LISTENER_STATE["running"] = True
    LISTENER_STATE["port"] = port
    LISTENER_STATE["path"] = path
    LISTENER_STATE["socket"] = sock
    LISTENER_STATE["ctx"] = ctx
    LISTENER_STATE["last"] = None
    LISTENER_STATE["ip"] = _get_local_ip()

    if not _start_listener_thread():
        LISTENER_STATE["running"] = False
        LISTENER_STATE["socket"] = None
        try:
            sock.close()
        except:
            pass
        ctx.log("Fetch listen threading unavailable", "ERROR")
        return "offline"

    ip = LISTENER_STATE.get("ip")
    if isinstance(ip, str) and ip:
        ctx.log("Fetch listener online at http://%s:%s%s" % (ip, port, path))
    else:
        ctx.log("Fetch listener online at %s:%s%s" % ("0.0.0.0", port, path))
    return "online"


def get(ctx, *positional, url=None, max_bytes=None, timeout=None, path=None):
    helper = _load_http_helper()
    return helper.get(ctx, *positional, url=url, max_bytes=max_bytes, timeout=timeout, path=path)


def post(ctx, *positional, url=None, value=None, max_bytes=None, timeout=None, path=None):
    helper = _load_http_helper()
    return helper.post(ctx, *positional, url=url, value=value, max_bytes=max_bytes, timeout=timeout, path=path)


def response(ctx, *positional, field=None):
    helper = _load_http_helper()
    return helper.response(ctx, *positional, field=field)


def status(ctx, *positional, type=None):
    helper = _load_http_helper()
    return helper.status(ctx, *positional, type=type)


def headers(ctx):
    helper = _load_http_helper()
    return helper.headers(ctx)


def header(ctx, *positional, name=None):
    helper = _load_http_helper()
    return helper.header(ctx, *positional, name=name)


def get_module():
    return {
        "get": get,
        "post": post,
        "listen": listen,
        "response": response,
        "status": status,
        "headers": headers,
        "header": header
    }


def get_manifest():
    return {
        "name": "fetch",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["network", "http", "extension-module"]
    }
