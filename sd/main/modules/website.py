try:
    import socket
except:
    socket = None

try:
    import _thread
except:
    _thread = None

try:
    import threading
except:
    threading = None

import time

from core.storage.csv import append_csv
from _wifi_runtime import ensure_wifi, get_ip_address

STATE = {
    "running": False,
    "port": None,
    "website": None,
    "site_dir": None,
    "socket": None,
    "clients": 0,
    "ip": "127.0.0.1",
    "ctx": None
}


def join_path(base, name):
    if base.endswith("/"):
        return base + name
    return base + "/" + name


def get_data_path(ctx):
    return ctx.data_path + "/data.csv"


def decode_text(value):
    try:
        return value.decode()
    except:
        try:
            return value.decode("utf-8", "ignore")
        except:
            return str(value)


def sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except:
        time.sleep(ms / 1000)


def file_exists(path):
    try:
        with open(path, "rb"):
            return True
    except:
        return False


def get_content_type(path):
    if path.endswith(".html"):
        return "text/html"
    if path.endswith(".css"):
        return "text/css"
    if path.endswith(".js"):
        return "application/javascript"
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return "image/jpeg"
    return "text/plain"


def url_decode(value):
    value = value.replace("+", " ")
    result = ""
    i = 0

    while i < len(value):
        char = value[i]

        if char == "%" and i + 2 < len(value):
            try:
                result += chr(int(value[i + 1:i + 3], 16))
                i += 3
                continue
            except:
                pass

        result += char
        i += 1

    return result


def parse_form(body):
    data = {}
    text = decode_text(body)

    if not text:
        return data

    pairs = text.split("&")
    for pair in pairs:
        if not pair:
            continue

        if "=" in pair:
            key, value = pair.split("=", 1)
        else:
            key, value = pair, ""

        key = url_decode(key)
        value = url_decode(value)

        if key in data:
            current = data[key]
            if isinstance(current, list):
                current.append(value)
            else:
                data[key] = [current, value]
        else:
            data[key] = value

    return data


def parse_value(value):
    if isinstance(value, list):
        parsed = []
        i = 0

        while i < len(value):
            parsed.append(parse_value(value[i]))
            i += 1

        return parsed

    if value == "":
        return ""

    try:
        return int(value)
    except:
        pass

    return value


def save_submission(ctx, values):
    data_path = get_data_path(ctx)
    entry = {}

    for key in values:
        parsed = parse_value(values[key])
        entry[key] = parsed
        ctx.vars[key] = parsed

    ctx.vars["_website_last"] = entry
    rows = append_csv(data_path, entry)
    ctx.vars["_website_last_id"] = len(rows)
    ctx.log("Saved website entry with %s fields" % len(values))


def read_request(client):
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

    header_bytes = raw[:header_end]
    body = raw[header_end + 4:]
    header_text = decode_text(header_bytes)
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


def send_response(client, status, body, content_type="text/plain", extra_headers=None):
    if extra_headers is None:
        extra_headers = []

    if isinstance(body, str):
        body = body.encode()

    response = "HTTP/1.1 %s\r\n" % status
    response += "Content-Type: %s\r\n" % content_type
    response += "Content-Length: %s\r\n" % len(body)
    response += "Connection: close\r\n"

    for header in extra_headers:
        response += header + "\r\n"

    response += "\r\n"
    client.send(response.encode() + body)


def safe_site_path(site_dir, path):
    path = path.split("?", 1)[0]

    if path == "/":
        path = "/index.html"

    if ".." in path:
        return None

    path = path.lstrip("/")
    return join_path(site_dir, path)


def serve_file(client, site_dir, path):
    full_path = safe_site_path(site_dir, path)

    if full_path is None or not file_exists(full_path):
        send_response(client, "404 Not Found", "Not found")
        return

    with open(full_path, "rb") as f:
        data = f.read()

    send_response(client, "200 OK", data, get_content_type(full_path))


def handle_request(client):
    method, path, headers, body = read_request(client)

    if not method:
        return

    ctx = STATE["ctx"]
    site_dir = STATE["site_dir"]

    if method == "POST" and path.startswith("/submit"):
        values = parse_form(body)
        save_submission(ctx, values)
        send_response(
            client,
            "303 See Other",
            "",
            "text/plain",
            ["Location: /?saved=1"]
        )
        return

    if method == "GET":
        serve_file(client, site_dir, path)
        return

    send_response(client, "405 Method Not Allowed", "Method not allowed")


def run_server():
    sock = STATE["socket"]

    while STATE["running"]:
        try:
            client, addr = sock.accept()
        except Exception:
            continue

        STATE["clients"] += 1

        try:
            handle_request(client)
        except Exception as e:
            ctx = STATE["ctx"]
            if ctx:
                ctx.log("Website request failed: %s" % e, "ERROR")
        finally:
            try:
                client.close()
            except:
                pass


def start_thread():
    if _thread is not None:
        _thread.start_new_thread(run_server, ())
        return True

    if threading is not None:
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        return True

    return False


def start(ctx, port=8080, website=None):
    if socket is None:
        ctx.log("Socket support unavailable", "ERROR")
        return "offline"

    if not website:
        ctx.log("Missing website folder", "ERROR")
        return "offline"

    site_dir = join_path(join_path(ctx.app_path, "Resources"), website)

    if not file_exists(join_path(site_dir, "index.html")):
        ctx.log("Website index.html not found", "ERROR")
        return "offline"

    if STATE["running"]:
        return "online"

    try:
        port = int(port)
    except:
        port = 8080

    ensure_wifi(ctx, label="website")

    try:
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.listen(2)

        try:
            sock.settimeout(1)
        except:
            pass

    except Exception as e:
        ctx.log("Website start failed: %s" % e, "ERROR")
        try:
            sock.close()
        except:
            pass
        return "offline"

    STATE["running"] = True
    STATE["port"] = port
    STATE["website"] = website
    STATE["site_dir"] = site_dir
    STATE["socket"] = sock
    STATE["clients"] = 0
    STATE["ip"] = get_ip_address()
    STATE["ctx"] = ctx

    if not start_thread():
        ctx.log("No background threading support for website", "ERROR")
        STATE["running"] = False
        try:
            sock.close()
        except:
            pass
        return "offline"

    ctx.log("Website online at http://%s:%s/" % (STATE["ip"], port))
    return "online"


def status(ctx):
    if STATE["running"]:
        return "online"
    return "offline"


def get(ctx, *positional, field=None):
    if positional:
        field = positional[0]

    data = {
        "status": status(ctx),
        "ip": STATE["ip"],
        "clients": STATE["clients"],
        "port": STATE["port"],
        "website": STATE["website"]
    }

    if field:
        return data.get(str(field).lower())

    return data


def stop(ctx):
    if not STATE["running"]:
        return "offline"

    STATE["running"] = False

    try:
        STATE["socket"].close()
    except:
        pass

    try:
        wake = socket.socket()
        wake.connect(("127.0.0.1", STATE["port"]))
        wake.close()
    except:
        pass

    STATE["socket"] = None
    ctx.log("Website offline")
    return "offline"


def get_module():
    return {
        "start": start,
        "status": status,
        "get": get,
        "stop": stop
    }


def get_manifest():
    return {
        "name": "website",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["network", "website", "extension-module"]
    }
