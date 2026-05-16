# /os/core/parser.py

class Parser:
    def __init__(self):
        pass

    def parse_value(self, token):
        token = token.strip()

        # Expression: ( ... )
        if token.startswith("(") and token.endswith(")"):
            return {
                "type": "expression",
                "value": token[1:-1]
            }

        # String
        if token.startswith('"') and token.endswith('"'):
            return {
                "type": "literal",
                "value": token[1:-1]
            }

        # Number
        try:
            return int(token)
        except:
            pass

        return token

    def tokenize(self, line):
        tokens = []
        current = ""
        depth = 0
        in_string = False

        i = 0
        while i < len(line):
            char = line[i]

            # Handle strings
            if char == '"':
                in_string = not in_string
                current += char

            # Handle parentheses
            elif char == "(" and not in_string:
                depth += 1
                current += char

            elif char == ")" and not in_string:
                depth -= 1
                current += char

            # Split only if safe
            elif char == " " and not in_string and depth == 0:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

            i += 1

        if current:
            tokens.append(current)

        return tokens

    def split_named_arg(self, token):
        depth = 0
        in_string = False

        i = 0
        while i < len(token):
            char = token[i]

            if char == '"':
                in_string = not in_string
            elif not in_string:
                if char == "(":
                    depth += 1
                elif char == ")" and depth > 0:
                    depth -= 1
                elif char == "=" and depth == 0:
                    return token[:i], token[i + 1:]

            i += 1

        return None, None

    def parse_line(self, line):
        line = line.strip()

        if not line or line.startswith("#"):
            return None

        # --- SET ---
        elif line.startswith("set"):
            parts = line.split(" ", 3)
            var = parts[1]

            if parts[2] != "to":
                raise Exception("Invalid set syntax")

            value = self.parse_value(parts[3])

            return {
                "type": "set",
                "var": var,
                "value": value
            }

        # --- IF ---
        if line.startswith("if "):
            condition = line[3:]
            return {
                "type": "if",
                "condition": condition
            }

        if line == "else":
            return {"type": "else"}

        if line.startswith("while "):
            condition = line[6:]
            return {
                "type": "while",
                "condition": condition
            }

        if line == "end":
            return {"type": "end"}

        if line == "stop":
            return {"type": "stop"}

        if line == "skip":
            return {"type": "skip"}

        # --- FOREACH ---
        if line.startswith("foreach "):
            parts = line.split()
            return {
                "type": "foreach",
                "var": parts[1],
                "iterable": parts[3]
            }

        # --- EVENT ---
        if line.startswith("on "):
            parts = line.split()
            return {
                "type": "event",
                "module": parts[1],
                "action": parts[2]
            }

        # --- MODULE COMMAND ---
        tokens = self.tokenize(line)
        module = tokens[0]
        action = tokens[1] if len(tokens) > 1 else None
        start_index = 2

        if module == "comm" and len(tokens) > 2 and tokens[1] not in ("get", "scan", "list"):
            action = tokens[2]
            start_index = 3

        positional = []
        args = {}

        if module == "comm" and len(tokens) > 1 and tokens[1] not in ("get", "scan", "list"):
            positional.append({
                "type": "literal",
                "value": tokens[1]
            })

        for token in tokens[start_index:]:
            key, value = self.split_named_arg(token)

            if key is not None:
                parsed = self.parse_value(value)

                if key in args:
                    current = args[key]
                    if isinstance(current, list):
                        current.append(parsed)
                    else:
                        args[key] = [current, parsed]
                else:
                    args[key] = parsed
            else:
                positional.append(self.parse_value(token))

        return {
            "type": "command",
            "module": module,
            "action": action,
            "positional": positional,
            "args": args
        }

    def parse_script(self, filepath):
        with open(filepath) as f:
            for line in f:
                instr = self.parse_line(line)
                if instr:
                    yield instr
