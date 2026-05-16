LIST_SEPARATOR = "|"


def stringify(value):
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        parts = []
        i = 0
        while i < len(value):
            parts.append(stringify(value[i]))
            i += 1
        return LIST_SEPARATOR.join(parts)
    return str(value)


def parse_scalar(value):
    if value == "":
        return ""
    if LIST_SEPARATOR in value:
        parts = value.split(LIST_SEPARATOR)
        result = []
        i = 0
        while i < len(parts):
            result.append(parse_scalar(parts[i]))
            i += 1
        return result
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except:
        return value


def escape_field(value):
    text = stringify(value)
    if "," in text or '"' in text or "\n" in text or "\r" in text:
        return '"' + text.replace('"', '""') + '"'
    return text


def parse_csv_line(line):
    row = []
    current = ""
    in_quotes = False
    i = 0

    while i < len(line):
        char = line[i]

        if in_quotes:
            if char == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    current += '"'
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue

            current += char
            i += 1
            continue

        if char == '"':
            in_quotes = True
            i += 1
            continue

        if char == ",":
            row.append(current)
            current = ""
            i += 1
            continue

        current += char
        i += 1

    row.append(current)
    return row


def load_rows(filepath):
    rows = []

    try:
        with open(filepath, "r") as f:
            for raw in f:
                line = raw.rstrip("\n").rstrip("\r")
                if line == "":
                    continue
                rows.append(parse_csv_line(line))
    except:
        return []

    return rows


def read_csv(filepath):
    rows = load_rows(filepath)
    if not rows:
        return []

    headers = rows[0]
    result = []
    i = 1

    while i < len(rows):
        row = rows[i]
        item = {}
        j = 0
        while j < len(headers):
            header = headers[j]
            value = ""
            if j < len(row):
                value = parse_scalar(row[j])
            item[header] = value
            j += 1
        result.append(item)
        i += 1

    return result


def collect_headers(existing_rows, new_rows):
    headers = []
    seen = {}

    def add_header(name):
        if name not in seen:
            seen[name] = True
            headers.append(name)

    i = 0
    while i < len(existing_rows):
        row = existing_rows[i]
        for key in row:
            add_header(key)
        i += 1

    i = 0
    while i < len(new_rows):
        row = new_rows[i]
        for key in row:
            add_header(key)
        i += 1

    return headers


def normalize_row(value):
    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        row = {}
        i = 0
        while i < len(value):
            row["value%s" % i] = value[i]
            i += 1
        return row

    return {"value": value}


def append_csv(filepath, value):
    rows = read_csv(filepath)
    to_add = []

    if isinstance(value, list):
        i = 0
        while i < len(value):
            to_add.append(normalize_row(value[i]))
            i += 1
    else:
        to_add.append(normalize_row(value))

    headers = collect_headers(rows, to_add)

    with open(filepath, "w") as f:
        header_line = []
        i = 0
        while i < len(headers):
            header_line.append(escape_field(headers[i]))
            i += 1
        f.write(",".join(header_line) + "\n")

        all_rows = rows + to_add
        i = 0
        while i < len(all_rows):
            row = all_rows[i]
            fields = []
            j = 0
            while j < len(headers):
                fields.append(escape_field(row.get(headers[j], "")))
                j += 1
            f.write(",".join(fields) + "\n")
            i += 1

    return to_add
