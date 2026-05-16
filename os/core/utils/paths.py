def split_path(path):
    if not isinstance(path, str):
        return []

    parts = []
    current = ""
    i = 0

    while i < len(path):
        char = path[i]
        if char == ".":
            if current:
                parts.append(current)
                current = ""
            i += 1
            continue
        current += char
        i += 1

    if current:
        parts.append(current)

    return parts


def get_path_value(value, path):
    current = value
    parts = split_path(path)
    i = 0

    while i < len(parts):
        part = parts[i]

        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
            i += 1
            continue

        if isinstance(current, list):
            if not part.isdigit():
                return None

            index = int(part)
            if index < 0 or index >= len(current):
                return None

            current = current[index]
            i += 1
            continue

        return None

    return current


def set_path_value(data, path, value):
    parts = split_path(path)
    if not parts:
        return False

    current = data
    i = 0

    while i < len(parts) - 1:
        part = parts[i]

        if isinstance(current, dict):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
            i += 1
            continue

        return False

    if not isinstance(current, dict):
        return False

    current[parts[-1]] = value
    return True

