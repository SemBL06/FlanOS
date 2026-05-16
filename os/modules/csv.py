from core.storage.csv import append_csv, read_csv
from core.utils.args import pick_arg


def get_csv_path(ctx, file=None):
    filename = file or "data.csv"
    if not isinstance(filename, str):
        filename = str(filename)
    if "/" in filename:
        return filename
    return ctx.data_path + "/" + filename


def append(ctx, *positional, file=None, value=None):
    file = pick_arg(positional, 0, file)
    value = pick_arg(positional, 1, value)
    resolved = ctx.executor.resolve(value)
    path = get_csv_path(ctx, file=file)
    rows = append_csv(path, resolved)
    ctx.vars["_csv_last"] = rows[-1]
    ctx.log("Appended %s row(s) to %s" % (len(rows), path))
    return rows


def get(ctx, *positional, row=None, name=None, header=None, file=None):
    if positional:
        first = positional[0]
        if file is None and isinstance(first, str) and (first.endswith(".csv") or "/" in first):
            file = first
            if len(positional) > 1 and row is None and name is None:
                second = positional[1]
                if isinstance(second, int) or (isinstance(second, str) and second.isdigit()):
                    row = second
                else:
                    header = second
            if len(positional) > 2 and name is None:
                name = positional[2]
        else:
            if row is None and name is None:
                if isinstance(first, int) or (isinstance(first, str) and first.isdigit()):
                    row = first
                else:
                    name = first

            if len(positional) > 1:
                second = positional[1]
                if row is not None and file is None and isinstance(second, str) and second.endswith(".csv"):
                    file = second
                elif header is None:
                    header = second

            if len(positional) > 2 and file is None:
                file = positional[2]

    path = get_csv_path(ctx, file=file)
    rows = read_csv(path)

    if row is not None:
        try:
            index = int(ctx.executor.resolve(row))
        except:
            ctx.log("Invalid csv row", "ERROR")
            return None

        if index < 1 or index > len(rows):
            return None
        return rows[index - 1]

    if name is not None and header is not None:
        wanted_name = ctx.executor.resolve(name)
        wanted_header = str(ctx.executor.resolve(header))
        i = 0
        while i < len(rows):
            current = rows[i]
            if current.get(wanted_header) == wanted_name:
                return current
            i += 1
        return None

    return rows


def get_module():
    return {
        "append": append,
        "get": get
    }
