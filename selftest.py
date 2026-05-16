import os
import sys

sys.path.insert(0, "os")
sys.path.insert(0, "sd/main/modules")

from core.context import Context
from core.executor import Executor
from core.parser import Parser

import modules.math as math_module
import modules.string as string_module
import modules.system as system_module
import modules.button as button_module
import modules.controls as controls_module
import modules.config as config_module
import modules.csv as csv_module
import modules.data as data_module
import modules.comm as comm_module
import modules.input as input_module
import modules.list as list_module
import modules.output as output_module
import wifi as wifi_module
import comm_bluetooth as bluetooth_module
import website as website_module
import fetch as fetch_module
import keyboard as keyboard_module
import mouse as mouse_module
import clock as clock_module
import modules.ui_core as ui_core_module
import modules.ui.options as options_module
import modules.ui.description as description_module
from core.storage.yaml import load_yaml, save_yaml
from core.storage.csv import read_csv
from core.utils.layout import resolve_position, text_start_x
from core.loaders.module_loader import load_builtin_modules, load_custom_drivers, load_custom_modules

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def fake_wifi_scan(ctx, duration=None, seconds=None):
    return [
        {"ssid": "Cool-Wifi", "type": "OPEN", "rssi": -30, "bssid": "B8:27:EB:12:34:56"},
        {"ssid": "Other-Wifi", "type": "WPA2-PSK", "rssi": -55, "bssid": "40:4E:36:AB:CD:EF"}
    ]


def fake_wifi_get(ctx, *positional, network=None):
    if not positional or not isinstance(network, dict):
        return None

    return network.get(positional[0])


def fake_input_get(ctx, name=None, config=None, positional=None, option=None, **kwargs):
    if name == "front_distance" and option == "meter":
        return 1.23
    return 512


def fake_output_set(ctx, name=None, config=None, positional=None, **kwargs):
    state = ctx.vars.get("_fake_output_state", {})
    if not isinstance(state, dict):
        state = {}

    value = {}
    for key in kwargs:
        value[key] = kwargs[key]

    if positional:
        if "on" in positional:
            value["state"] = "on"
        elif "off" in positional:
            value["state"] = "off"

    state[name] = value
    ctx.vars["_fake_output_state"] = state
    return value


def fake_output_get(ctx, name=None, config=None, positional=None, **kwargs):
    state = ctx.vars.get("_fake_output_state", {})
    if not isinstance(state, dict):
        state = {}

    current = state.get(name, {})
    if not isinstance(current, dict):
        return current

    field = kwargs.get("field")
    if isinstance(field, str):
        return current.get(field)
    return current


class FakeHID:
    def __init__(self):
        self.history = []

    def keyboard_hold(self, keys):
        self.history.append(("keyboard_hold", list(keys)))

    def keyboard_release(self, keys):
        self.history.append(("keyboard_release", list(keys)))

    def keyboard_release_all(self):
        self.history.append(("keyboard_release_all",))

    def keyboard_type(self, text):
        self.history.append(("keyboard_type", text))

    def keyboard_press(self, keys, delay):
        self.history.append(("keyboard_press", list(keys), delay))

    def mouse_move(self, x, y):
        self.history.append(("mouse_move", x, y))

    def mouse_click(self, button):
        self.history.append(("mouse_click", button))

    def mouse_hold(self, button):
        self.history.append(("mouse_hold", button))

    def mouse_release(self, button):
        self.history.append(("mouse_release", button))

    def mouse_release_all(self):
        self.history.append(("mouse_release_all",))

    def mouse_scroll(self, amount):
        self.history.append(("mouse_scroll", amount))


class FakeButtons:
    def __init__(self):
        self.clicked = ["", "", "left", "down", "left", "down", "down", "right", "down", "left", "right"]
        self.states = {
            "up": False,
            "down": False,
            "left": False,
            "right": False
        }

    def get_clicked(self):
        if not self.clicked:
            return ""
        return self.clicked.pop(0)

    def get_state(self, name):
        return bool(self.states.get(name, False))


class FakeScriptRunner:
    def __init__(self):
        self.called = []

    def __call__(self, path):
        self.called.append(path)


class JsonHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/json":
            body = json.dumps({"weather": {"temp": 12}, "source": "local"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/updates":
            body = json.dumps({
                "modules": {
                    "wifi": {"version": "1.2.0", "url": "https://example.com/wifi.py"},
                    "fetch": {"version": "1.0.0", "url": "https://example.com/fetch.py"}
                }
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path != "/json":
            self.send_response(404)
            self.end_headers()
            return

    def do_POST(self):
        if self.path != "/json":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        data = json.loads(raw.decode())
        body = json.dumps({"received": data, "ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def run():
    original_main_config = load_yaml("sd/main/main.yml")
    expected_ssid = ""
    if isinstance(original_main_config, dict):
        expected_ssid = original_main_config.get("wifi", {}).get("SSID", "")
        working_main_config = dict(original_main_config)
    else:
        working_main_config = {}

    working_main_config["input"] = {
        "front_distance": {
            "driver": "fake_sensor",
            "pin": 1
        }
    }
    working_main_config["output"] = {
        "led": {
            "driver": "fake_output",
            "pin": 2
        }
    }
    working_main_config["fetch"] = {
        "updates_url": "http://127.0.0.1:8092/updates"
    }
    save_yaml("sd/main/main.yml", working_main_config)
    data_file_exists = os.path.exists("sd/scripts/data.yml")
    original_data = load_yaml("sd/scripts/data.yml")
    custom_override_path = "sd/main/modules/string.py"
    custom_broken_path = "sd/main/modules/broken.py"
    json_server = None
    try:
        json_server = HTTPServer(("127.0.0.1", 8092), JsonHandler)
        json_thread = threading.Thread(target=json_server.serve_forever)
        json_thread.daemon = True
        json_thread.start()

        try:
            with open("sd/scripts/networks.csv", "w") as f:
                f.write("")
        except:
            pass

        try:
            with open("sd/scripts/website/data.csv", "w") as f:
                f.write("")
        except:
            pass

        ctx = Context(app_path="sd/scripts", data_path="sd/scripts")
        executor = Executor(ctx)
        ctx.executor = executor
        ctx.hid = FakeHID()
        ctx.buttons = FakeButtons()
        fake_runner = FakeScriptRunner()
        executor.execute_script = fake_runner

        executor.register_module("math", math_module.get_module())
        executor.register_module("string", string_module.get_module())
        executor.register_module("display", system_module.get_module())
        executor.register_module("log", system_module.get_module())
        executor.register_module("system", system_module.get_module())
        executor.register_module("button", button_module.get_module())
        executor.register_module("controls", controls_module.get_module())
        executor.register_module("ui", ui_core_module.get_module())
        executor.register_module("config", config_module.get_module())
        executor.register_module("csv", csv_module.get_module())
        executor.register_module("data", data_module.get_module())
        executor.register_module("comm", comm_module.get_module())
        executor.register_module("input", input_module.get_module())
        executor.register_module("output", output_module.get_module())
        executor.register_module("list", list_module.get_module())
        executor.register_module("fetch", fetch_module.get_module())
        executor.register_module("keyboard", keyboard_module.get_module())
        executor.register_module("mouse", mouse_module.get_module())
        executor.register_module("clock", clock_module.get_module())
        executor.register_module("options", options_module.get_module())
        executor.register_module("description", description_module.get_module())
        executor.register_module("wifi", {
            "scan": fake_wifi_scan,
            "get": wifi_module.get
        })
        executor.register_module("bluetooth", {
            "get": bluetooth_module.get
        })
        ctx.vars["_capability_providers"] = {
            "comm": {
                "wifi": {
                    "scan": fake_wifi_scan,
                    "get": wifi_module.get
                },
                "bluetooth": {
                    "get": bluetooth_module.get
                }
            },
            "input": {
                "fake_sensor": {
                    "get": fake_input_get
                }
            },
            "output": {
                "fake_output": {
                    "set": fake_output_set,
                    "get": fake_output_get
                }
            }
        }
        ctx.vars["_module_manifests"] = {
            "wifi": {"version": "0.9.0"},
            "fetch": {"version": "1.0.0"}
        }

        parser = Parser()
        source = [
            'set total to (math add a=1 b=1)',
            'set loose_total to (math add 3 4)',
            'log info (string concat a="Result: " b=total)',
            'set total_msg to (string concat a="Nested: " b=(math add a=2 b=3))',
            'set loop_count to 0',
            'while on',
            '    set loop_count to (math add loop_count 1)',
            '    if loop_count == 2',
            '        skip',
            '    end',
            '    if loop_count == 4',
            '        stop',
            '    end',
            '    set loop_seen to (list add items=loop_seen value=loop_count)',
            'end',
            'if 1 == 2',
            '    set branch to "if"',
            'else',
            '    set branch to "else"',
            'end',
            'set scan to (comm wifi scan seconds=2)',
            'foreach i in 1-3',
            '    set counted_last to i',
            'end',
            'foreach wifi in scan',
            '    set name to (comm wifi get value=ssid network=wifi)',
            'end',
            'set selected to (ui options list=scan field=ssid selected=0)',
            'set ui_description_value to (ui description text=selected title="Network Info")',
            'set selected_ssid to selected.ssid',
            'set selected_security to selected.type',
            'set first_scan_ssid to scan.0.ssid',
            'set greeting to "Hello {selected.ssid}"',
            'set joined_loose to (string concat "SSID: " selected.ssid)',
            'set wifi_vendor to (comm wifi get value=vendor network=selected)',
            'set ble_vendor to (comm bluetooth get value=vendor device=btdevice)',
            'set current_ssid to (data get file="main" path="wifi.SSID")',
            'data save file="main" path="wifi.SSID" value="LabWifi"',
            'set updated_ssid_positional to (data get "main" "wifi.SSID")',
            'set updated_ssid to (data get file="main" path="wifi.SSID")',
            'set puddings to (list add value="vanilla")',
            'set puddings to (list add items=puddings value="chocolate")',
            'set puddings to (list add puddings "banana")',
            'set has_chocolate to (list contains items=puddings value="chocolate")',
            'set second_pudding to (list get items=puddings index=1)',
            'set pudding_count to (list length items=puddings)',
            'set puddings_without_chocolate to (list remove items=puddings value="chocolate")',
            'set saved_name to (data save file="data" path="session.network.name" value=selected.ssid)',
            'set nested_name to (data get file="data" path="session.network.name")',
            'set saved_bssid to (data save file="data" path="session.network.bssid" value=selected.bssid)',
            'set names_list to (data append file="data" path="session.network.names" value=selected.ssid)',
            'csv append "networks.csv" scan',
            'set first_network to (csv get "networks.csv" 1)',
            'set named_network to (csv get "networks.csv" "ssid" "Cool-Wifi")',
            'set first_network_loose to (csv get row=1 file="networks.csv")',
            'set named_network_loose to (csv get name="Cool-Wifi" header="ssid" file="networks.csv")',
            'set weather to (fetch get url="http://127.0.0.1:8092/json" max_bytes=2048)',
            'set weather_temp to (fetch get url="http://127.0.0.1:8092/json" path="weather.temp" max_bytes=2048)',
            'set payload to selected',
            'set posted to (fetch post url="http://127.0.0.1:8092/json" value=payload max_bytes=2048)',
            'set posted_ok to posted.ok',
            'set posted_ssid to (fetch post url="http://127.0.0.1:8092/json" value=payload path="received.ssid" max_bytes=2048)',
            'set fetch_status to (fetch status)',
            'set fetch_ok to (fetch status ok)',
            'set fetch_header_type to (fetch header name="Content-Type")',
            'set updates to (fetch get updates url="http://127.0.0.1:8092/updates")',
            'set fetch_listener to (fetch listen port=8093 path="/trigger-led")',
            'set display_result to (display print text=selected.ssid)',
            'set log_result to (log info text=selected.ssid)',
            'set print_result to (display print "SSID: {selected_ssid}")',
            'set printed_log to (log info "Hello {selected.ssid}")',
            'set warned_log to (log warn "Careful {selected.ssid}")',
            'set debugged_log to (log debug "Debug {selected.ssid}")',
            'set cleared to (display clear)',
            'set inverted to (display invert)',
            'set shape_result to (display shapes BOX text="Hello" x=center y=top)',
            'set image_result to (display image image="sd/scripts/website/Resources/Website1/index.png" position=top_right)',
            'set list_display to (display print scan)',
            'set left_alias to controls.left',
            'set left_pressed to (controls pressed state=left)',
            'if (button get clicked) == (button get state=left)',
            '    set clicked_state_match to 1',
            'end',
            'if (button get clicked) == button.down',
            '    set clicked_alias_match to 1',
            'end',
            'if button get clicked == button.left',
            '    set cursor_pick to (system cursor position)',
            'end',
            'if (button get clicked) == button.down',
            '    options move direction=down',
            'end',
            'set cursor_after_move to (system cursor position)',
            'set cursor_index to (system cursor index)',
            'set script_menu to (system scripts)',
            'set ui_menu_state to (ui options list=script_menu field=name selected=0)',
            'set ui_menu_back to (ui description text=ui_menu_state title="Menu Item")',
            'options show items=script_menu field=name selected=0',
            'system run selected',
            'system run script="/sd/scripts/test2/main.fl"',
            'set menu_state to (options interact items=script_menu field=name selected=0)',
            'set menu_state to (options interact run=true)',
            'set menu_back to (options interact)',
            'set sensor_reading to (input get front_distance option=meter)',
            'output set led on',
            'set led_pwm to (output set led pwm=128)',
            'set led_pwm_value to (output get led field="pwm")',
            'set clock_day_text to (clock get day text)',
            'set clock_month_text to (clock get month text)',
            'keyboard hold key=SUPER key=r',
            'keyboard print text="https://google.com/"',
            'keyboard press key=ENTER',
            'keyboard release key=SUPER key=r',
            'mouse move x=1000 y=200',
            'mouse move position="top right"',
            'mouse click type=right',
            'mouse scroll amount=-2'
        ]

        ctx.vars["btdevice"] = {
            "name": "Pi Sensor",
            "addr": "B8:27:EB:AA:BB:CC"
        }

        instructions = []
        for line in source:
            parsed = parser.parse_line(line)
            if parsed:
                instructions.append(parsed)

        executor.execute(instructions)

        listen_conn = http.client.HTTPConnection("127.0.0.1", 8093, timeout=5)
        listen_payload = json.dumps({"player": "SemBL"}).encode()
        listen_conn.request(
            "POST",
            "/trigger-led",
            listen_payload,
            {"Content-Type": "application/json", "Content-Length": str(len(listen_payload))}
        )
        listen_response = listen_conn.getresponse()
        listen_body = listen_response.read().decode()
        listen_conn.close()

        ctx.vars["listen_status_code"] = listen_response.status
        ctx.vars["listen_body_text"] = listen_body
        ctx.vars["listen_last_payload"] = fetch_module.listen(ctx, "get")
        ctx.vars["listen_last_player"] = fetch_module.listen(ctx, "get", field="player")
        ctx.vars["listen_status"] = fetch_module.listen(ctx, "status")
        fetch_module.listen(ctx, "stop")

        assert ctx.vars["total"] == 2
        assert ctx.vars["loose_total"] == 7
        assert ctx.vars["total_msg"] == "Nested: 5"
        assert ctx.vars["loop_count"] == 4
        assert ctx.vars["loop_seen"] == [1, 3]
        assert ctx.vars["branch"] == "else"
        assert isinstance(ctx.vars["scan"], list)
        assert ctx.vars["counted_last"] == 3
        assert ctx.vars["scan"][0]["ssid"] == "Cool-Wifi"
        assert ctx.vars["name"] == "Other-Wifi"
        assert ctx.vars["selected"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["ui_description_value"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["selected_ssid"] == "Cool-Wifi"
        assert ctx.vars["selected_security"] == "OPEN"
        assert ctx.vars["first_scan_ssid"] == "Cool-Wifi"
        assert ctx.vars["greeting"] == "Hello Cool-Wifi"
        assert ctx.vars["joined_loose"] == "SSID: Cool-Wifi"
        assert ctx.vars["wifi_vendor"] == "Raspberry Pi"
        assert ctx.vars["ble_vendor"] == "Raspberry Pi"
        assert ctx.vars["current_ssid"] == expected_ssid
        assert ctx.vars["updated_ssid_positional"] == "LabWifi"
        assert ctx.vars["updated_ssid"] == "LabWifi"
        assert ctx.vars["puddings"] == ["vanilla", "chocolate", "banana"]
        assert ctx.vars["has_chocolate"] is True
        assert ctx.vars["second_pudding"] == "chocolate"
        assert ctx.vars["pudding_count"] == 3
        assert ctx.vars["puddings_without_chocolate"] == ["vanilla", "banana"]
        assert ctx.vars["saved_name"] == "Cool-Wifi"
        assert ctx.vars["nested_name"] == "Cool-Wifi"
        assert ctx.vars["saved_bssid"] == "B8:27:EB:12:34:56"
        assert ctx.vars["names_list"] == ["Cool-Wifi"]
        assert ctx.vars["first_network"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["named_network"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["first_network_loose"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["named_network_loose"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["weather"]["weather"]["temp"] == 12
        assert ctx.vars["weather_temp"] == 12
        assert ctx.vars["posted_ok"] is True
        assert ctx.vars["posted_ssid"] == "Cool-Wifi"
        assert ctx.vars["fetch_status"] == 200
        assert ctx.vars["fetch_ok"] is True
        assert "application/json" in ctx.vars["fetch_header_type"]
        assert len(ctx.vars["updates"]) == 1
        assert ctx.vars["updates"][0]["name"] == "wifi"
        assert ctx.vars["updates"][0]["version"] == "1.2.0"
        assert ctx.vars["fetch_listener"] == "online"
        assert ctx.vars["listen_status_code"] == 200
        assert "success" in ctx.vars["listen_body_text"]
        assert ctx.vars["listen_last_payload"]["player"] == "SemBL"
        assert ctx.vars["listen_last_player"] == "SemBL"
        assert ctx.vars["listen_status"] == "online"
        assert ctx.vars["display_result"] == "Cool-Wifi"
        assert ctx.vars["log_result"] == "Cool-Wifi"
        assert ctx.vars["print_result"] == "SSID: Cool-Wifi"
        assert ctx.vars["printed_log"] == "Hello Cool-Wifi"
        assert ctx.vars["warned_log"] == "Careful Cool-Wifi"
        assert ctx.vars["debugged_log"] == "Debug Cool-Wifi"
        assert ctx.vars["cleared"] is True
        assert ctx.vars["inverted"] is True
        assert ctx.vars["shape_result"]["shape"] == "BOX"
        assert ctx.vars["shape_result"]["x"] == 5
        assert ctx.vars["shape_result"]["y"] == 0
        assert ctx.vars["image_result"]["x"] == 15
        assert ctx.vars["image_result"]["y"] == 0
        assert ctx.vars["list_display"] == ctx.vars["scan"]
        assert ctx.vars["left_alias"] == "left"
        assert ctx.vars["left_pressed"] is False
        assert ctx.vars["clicked_state_match"] == 1
        assert ctx.vars["clicked_alias_match"] == 1
        assert ctx.vars["_description_last"]["title"] is None
        assert ctx.vars["_description_last"]["lines"] == []
        assert ctx.vars["_options_last"] == []
        assert ctx.vars["cursor_pick"]["ssid"] == "Cool-Wifi"
        assert ctx.vars["cursor_after_move"]["ssid"] == "Other-Wifi"
        assert ctx.vars["cursor_index"] == 1
        assert ctx.vars["ui_menu_state"]["name"] == ctx.vars["script_menu"][1]["name"]
        assert ctx.vars["ui_menu_back"] == "back"
        assert len(fake_runner.called) == 3
        assert fake_runner.called[0] == ctx.vars["script_menu"][0]["path"]
        assert fake_runner.called[1] == "/sd/scripts/test2/main.fl"
        assert fake_runner.called[2] == ctx.vars["menu_state"]["path"]
        assert ctx.vars["menu_state"]["name"] == ctx.vars["script_menu"][1]["name"]
        assert ctx.vars["menu_back"] == "back"
        assert ctx.vars["sensor_reading"] == 1.23
        assert ctx.vars["led_pwm"]["pwm"] == 128
        assert ctx.vars["led_pwm_value"] == 128
        assert isinstance(ctx.vars["clock_day_text"], str) and ctx.vars["clock_day_text"] != ""
        assert isinstance(ctx.vars["clock_month_text"], str) and ctx.vars["clock_month_text"] != ""
        assert ctx.hid.history[0] == ("keyboard_hold", ["WINDOWS", "R"])
        assert ctx.hid.history[1] == ("keyboard_type", "https://google.com/")
        assert ctx.hid.history[2] == ("keyboard_press", ["ENTER"], 40)
        assert ctx.hid.history[3] == ("keyboard_release", ["WINDOWS", "R"])
        assert ctx.hid.history[4] == ("mouse_move", 1000, 200)
        assert ctx.hid.history[5] == ("mouse_move", 4000, -4000)
        assert ctx.hid.history[6] == ("mouse_click", "right")
        assert ctx.hid.history[7] == ("mouse_scroll", -2)
        assert any("Result: 2" in log for log in ctx.logs)
        assert any("[WARN] Careful Cool-Wifi" in log for log in ctx.logs)
        assert any("[DEBUG] Debug Cool-Wifi" in log for log in ctx.logs)
        assert text_start_x("Hello") == 5
        assert resolve_position(position="top_right", text="Hello") == {"x": 15, "y": 0}
        assert resolve_position(x="center", y="bottom", text="Hello") == {"x": 5, "y": 7}

        website_ctx = Context(
            app_path="sd/scripts/website",
            data_path="sd/scripts/website"
        )
        website_executor = Executor(website_ctx)
        website_ctx.executor = website_executor
        website_executor.register_module("website", website_module.get_module())
        website_executor.register_module("csv", csv_module.get_module())

        result = website_module.start(website_ctx, port=8091, website="Website1")
        assert result == "online"
        assert website_module.status(website_ctx) == "online"
        assert website_executor.resolve("website.status") == "online"
        assert website_executor.resolve("website.get")["website"] == "Website1"

        sleep = getattr(__import__("time"), "sleep")
        sleep(0.2)

        conn = http.client.HTTPConnection("127.0.0.1", 8091, timeout=5)
        conn.request(
            "POST",
            "/submit",
            "pudding=Ofcourse+I+do%21&name=Sem&texture=smooth&kindofpudding=vanilla&likeness=100&toppings=sprinkles&toppings=cherries&favoriteflavors=vanilla&favoriteflavors=banana",
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        response = conn.getresponse()
        assert response.status == 303
        conn.close()

        sleep(0.2)

        saved = read_csv("sd/scripts/website/data.csv")
        assert saved[0]["pudding"] == "Ofcourse I do!"
        assert saved[0]["name"] == "Sem"
        assert saved[0]["texture"] == "smooth"
        assert saved[0]["kindofpudding"] == "vanilla"
        assert saved[0]["likeness"] == 100
        assert saved[0]["toppings"] == ["sprinkles", "cherries"]
        assert saved[0]["favoriteflavors"] == ["vanilla", "banana"]
        assert website_module.get(website_ctx, "clients") >= 1
        assert website_executor.resolve("website.clients") >= 1
        assert website_executor.resolve("website.port") == 8091
        assert website_module.stop(website_ctx) == "offline"
        with open(custom_override_path, "w") as f:
            f.write(
                'def get_module():\n'
                '    return {"concat": lambda ctx, a=None, b=None: "OVERRIDE"}\n'
                '\n'
                'def get_manifest():\n'
                '    return {"name": "string", "version": "9.9.9", "author": "Override", "board": "any", "dependencies": [], "capabilities": ["override"]}\n'
            )

        with open(custom_broken_path, "w") as f:
            f.write(
                'def get_module():\n'
                '    return {"ping": lambda ctx: "broken"}\n'
                '\n'
                'def get_manifest():\n'
                '    return {"name": "broken", "dependencies": "not-a-list"}\n'
            )

        loader_ctx = Context(app_path="sd/main", data_path="sd/main")
        loader_executor = Executor(loader_ctx)
        loader_ctx.executor = loader_executor
        load_builtin_modules(loader_executor, loader_ctx)
        assert "fetch" not in loader_executor.modules
        assert "wifi" not in loader_executor.modules
        assert "bluetooth" not in loader_executor.modules
        assert "keyboard" not in loader_executor.modules
        assert "mouse" not in loader_executor.modules
        assert "website" not in loader_executor.modules
        assert "clock" not in loader_executor.modules
        assert "comm" in loader_executor.modules
        assert "ui" in loader_executor.modules
        assert "controls" in loader_executor.modules
        loaded_drivers = load_custom_drivers(loader_executor, loader_ctx, original_main_config)
        loaded_custom = load_custom_modules(loader_executor, loader_ctx, original_main_config)

        assert "ultrasonic" in loaded_drivers
        assert "oled" in loaded_drivers
        assert "dht11" in loaded_drivers
        assert "pn532" in loaded_drivers
        assert "sd_spi" in loaded_drivers
        assert "demo" in loaded_custom
        assert "fetch" in loaded_custom
        assert "wifi" in loaded_custom
        assert "bluetooth" in loaded_custom
        assert "keyboard" in loaded_custom
        assert "mouse" in loaded_custom
        assert "website" in loaded_custom
        assert "clock" in loaded_custom
        assert "demo" in loader_executor.modules
        assert "lcd_i2c" not in loader_executor.modules
        assert "oled" not in loader_executor.modules
        assert "dht11" not in loader_executor.modules
        assert "pn532" not in loader_executor.modules
        assert "ultrasonic" not in loader_executor.modules
        assert "sd_spi" in loader_executor.modules
        assert "wifi" not in loader_executor.modules
        assert "bluetooth" not in loader_executor.modules
        assert loader_executor.evaluate_expression("demo ping") == "pong"
        assert loader_executor.resolve("demo.status") == "ready"
        assert loader_ctx.vars["_display_provider_name"] == "oled"
        assert "ultrasonic" in loader_ctx.vars["_capability_providers"]["input"]
        assert "dht11" in loader_ctx.vars["_capability_providers"]["input"]
        assert "pn532" in loader_ctx.vars["_capability_providers"]["input"]
        assert "wifi" in loader_ctx.vars["_capability_providers"]["comm"]
        assert "bluetooth" in loader_ctx.vars["_capability_providers"]["comm"]
        assert loader_executor.evaluate_expression("comm wifi scan") == []
        assert loader_executor.evaluate_expression("clock get day") is not None
        assert loader_executor.evaluate_expression("fetch status") is None
        assert loader_executor.evaluate_expression("display clear") is True
        assert loader_executor.evaluate_expression('display print text="Hello LCD" x=center y=0') == "Hello LCD"
        assert loader_ctx.vars["_display_last"][0]["x"] == 3
        assert loader_ctx.vars["_module_manifests"]["demo"]["version"] == "1.0.0"
        assert loader_ctx.vars["_module_manifests"]["demo"]["author"] == "FlanLang"
        assert loader_ctx.vars["_module_manifests"]["demo"]["capabilities"] == ["example", "custom-module"]
        if "lcd_i2c" in loader_ctx.vars["_module_manifests"]:
            assert loader_ctx.vars["_module_manifests"]["lcd_i2c"]["capabilities"] == ["display-provider", "i2c", "lcd"]
        assert loader_ctx.vars["_module_manifests"]["fetch"]["capabilities"] == ["network", "http", "extension-module"]
        assert loader_ctx.vars["_module_sources"]["string"] == "builtin:modules.string"
        assert loader_executor.evaluate_expression('string concat a="A" b="B"') == "AB"
        assert "broken" not in loader_executor.modules
        assert any("Skipping module override for string" in log for log in loader_ctx.logs)
        assert any("Invalid manifest field dependencies for module broken" in log for log in loader_ctx.logs)

        print("Self-test passed")
    finally:
        try:
            json_server.shutdown()
        except:
            pass
        try:
            json_server.server_close()
        except:
            pass
        save_yaml("sd/main/main.yml", original_main_config)
        if data_file_exists:
            save_yaml("sd/scripts/data.yml", original_data)
        else:
            try:
                os.remove("sd/scripts/data.yml")
            except:
                pass
        try:
            os.remove("sd/scripts/networks.csv")
        except:
            pass
        try:
            os.remove("sd/scripts/website/data.csv")
        except:
            pass
        try:
            os.remove(custom_override_path)
        except:
            pass
        try:
            os.remove(custom_broken_path)
        except:
            pass


if __name__ == "__main__":
    run()
