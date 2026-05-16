VENDOR_FILES = (
    "/sd/main/Resources/mac.txt",
    "sd/main/Resources/mac.txt"
)

FALLBACK_PREFIXES = {
    "28CDC1": "Apple",
    "3C5AB4": "Google",
    "58EF68": "Samsung",
    "6466B3": "Cisco Meraki",
    "74DA38": "Ubiquiti",
    "A42BB0": "Nintendo",
    "B827EB": "Raspberry Pi",
    "DCA632": "Raspberry Pi",
    "E45F01": "Raspberry Pi",
    "FCFBFB": "Facebook"
}

LOOKUP_CACHE = {}
LOOKUP_CACHE_LIMIT = 32


def normalize_mac(value):
    if value is None:
        return ""

    text = str(value).upper().replace("-", "").replace(":", "")
    return text


def get_prefix(value):
    text = normalize_mac(value)

    if len(text) < 6:
        return ""

    return text[:6]


def remember(prefix, vendor):
    if len(LOOKUP_CACHE) >= LOOKUP_CACHE_LIMIT:
        for key in LOOKUP_CACHE:
            del LOOKUP_CACHE[key]
            break

    LOOKUP_CACHE[prefix] = vendor
    return vendor


def parse_vendor_line(line):
    text = line.strip()

    if not text:
        return None, None

    parts = text.split(None, 1)
    if len(parts) < 2:
        return None, None

    prefix = parts[0].upper()
    vendor = parts[1].strip()

    if len(prefix) < 6:
        return None, None

    return prefix[:6], vendor


def lookup_vendor_file(prefix):
    i = 0

    while i < len(VENDOR_FILES):
        path = VENDOR_FILES[i]
        i += 1

        try:
            with open(path, "r") as f:
                for line in f:
                    current_prefix, vendor = parse_vendor_line(line)
                    if current_prefix == prefix:
                        return vendor
        except:
            continue

    return None


def guess_vendor(value):
    prefix = get_prefix(value)

    if not prefix:
        return "UNKNOWN"

    if prefix in LOOKUP_CACHE:
        return LOOKUP_CACHE[prefix]

    vendor = lookup_vendor_file(prefix)
    if vendor:
        return remember(prefix, vendor)

    vendor = FALLBACK_PREFIXES.get(prefix, "UNKNOWN")
    return remember(prefix, vendor)
