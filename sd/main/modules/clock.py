try:
    import machine
except:
    machine = None

try:
    import time
except:
    time = None


MONTH_NAMES = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
)

DAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
)


def read_now():
    if machine is not None:
        try:
            return machine.RTC().datetime()
        except:
            pass

    if time is not None:
        try:
            return time.localtime()
        except:
            pass

    return (2000, 1, 1, 0, 0, 0, 0, 0)


def normalize_now():
    now = read_now()
    if len(now) >= 8:
        if len(now) > 7:
            return {
                "year": int(now[0]),
                "month": int(now[1]),
                "day": int(now[2]),
                "weekday": int(now[3]),
                "hour": int(now[4]),
                "minute": int(now[5]),
                "second": int(now[6])
            }

    return {
        "year": 2000,
        "month": 1,
        "day": 1,
        "weekday": 0,
        "hour": 0,
        "minute": 0,
        "second": 0
    }


def get_field_data():
    values = normalize_now()
    values["date"] = {
        "year": values["year"],
        "month": values["month"],
        "day": values["day"]
    }
    values["time"] = {
        "hour": values["hour"],
        "minute": values["minute"],
        "second": values["second"]
    }
    return values


def format_value(field, value):
    if field == "day":
        weekday = normalize_now().get("weekday", 0)
        if weekday < 0 or weekday >= len(DAY_NAMES):
            return str(value)
        return DAY_NAMES[weekday]

    if field == "month":
        if isinstance(value, int) and value >= 1 and value < len(MONTH_NAMES):
            return MONTH_NAMES[value]
        return str(value)

    if field == "date" and isinstance(value, dict):
        return "%04d-%02d-%02d" % (
            int(value.get("year", 0)),
            int(value.get("month", 0)),
            int(value.get("day", 0))
        )

    if field == "time" and isinstance(value, dict):
        return "%02d:%02d:%02d" % (
            int(value.get("hour", 0)),
            int(value.get("minute", 0)),
            int(value.get("second", 0))
        )

    return str(value)


def get(ctx, *positional, field=None, text=False):
    if field is None and positional:
        field = positional[0]
    if len(positional) > 1 and str(positional[1]).lower() == "text":
        text = True

    if not isinstance(field, str) or not field:
        ctx.log("Missing clock field", "ERROR")
        return None

    field = field.lower()
    values = get_field_data()
    value = values.get(field)
    if value is None:
        ctx.log("Unknown clock field %s" % field, "ERROR")
        return None

    if text:
        return format_value(field, value)

    return value


def get_module():
    return {
        "get": get
    }


def get_manifest():
    return {
        "name": "clock",
        "version": "1.0.0",
        "author": "FlanLang",
        "board": "any",
        "dependencies": [],
        "capabilities": ["time", "rtc", "extension-module"]
    }
