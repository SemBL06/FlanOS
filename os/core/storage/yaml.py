def parse_scalar(value):
    if value == '""' or value == "''":
        return ""

    if len(value) >= 2:
        if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
            return value[1:-1].replace('\\"', '"')

    if value == "true":
        return True
    if value == "false":
        return False
    if value == "null":
        return None

    try:
        return int(value)
    except:
        pass

    return value


def format_scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)

    text = str(value)
    return '"' + text.replace('"', '\\"') + '"'


def load_lines(filepath):
    lines = []

    with open(filepath, "r") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")

            if not line.strip():
                continue

            stripped = line.lstrip(" ")
            if stripped.startswith("#"):
                continue

            indent = len(line) - len(stripped)
            lines.append((indent, stripped))

    return lines


def parse_node(lines, index, indent):
    if index >= len(lines):
        return None, index

    current_indent, text = lines[index]

    if current_indent != indent:
        return None, index

    if text.startswith("- "):
        return parse_list(lines, index, indent)

    return parse_dict(lines, index, indent)


def parse_dict(lines, index, indent):
    data = {}

    while index < len(lines):
        current_indent, text = lines[index]

        if current_indent < indent:
            break

        if current_indent != indent or text.startswith("- "):
            break

        if ":" not in text:
            index += 1
            continue

        key, value = text.split(":", 1)
        key = key.strip()
        value = value.strip()
        index += 1

        if value:
            data[key] = parse_scalar(value)
            continue

        if index < len(lines) and lines[index][0] > current_indent:
            child, index = parse_node(lines, index, lines[index][0])
            data[key] = child
        else:
            data[key] = {}

    return data, index


def parse_list(lines, index, indent):
    data = []

    while index < len(lines):
        current_indent, text = lines[index]

        if current_indent < indent:
            break

        if current_indent != indent or not text.startswith("- "):
            break

        value = text[2:].strip()
        index += 1

        if value:
            data.append(parse_scalar(value))
            continue

        if index < len(lines) and lines[index][0] > current_indent:
            child, index = parse_node(lines, index, lines[index][0])
            data.append(child)
        else:
            data.append(None)

    return data, index


def load_yaml(filepath):
    try:
        lines = load_lines(filepath)
    except:
        return {}

    if not lines:
        return {}

    data, _ = parse_node(lines, 0, lines[0][0])
    return data


def write_node(f, value, indent):
    prefix = " " * indent

    if isinstance(value, dict):
        for key in value:
            item = value[key]

            if isinstance(item, (dict, list)):
                f.write("%s%s:\n" % (prefix, key))
                write_node(f, item, indent + 2)
            else:
                f.write("%s%s: %s\n" % (prefix, key, format_scalar(item)))
        return

    if isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                f.write("%s-\n" % prefix)
                write_node(f, item, indent + 2)
            else:
                f.write("%s- %s\n" % (prefix, format_scalar(item)))


def save_yaml(filepath, data):
    with open(filepath, "w") as f:
        write_node(f, data, 0)
