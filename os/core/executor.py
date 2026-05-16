# /os/core/executor.py
try:
    import gc
except:
    gc = None

class Executor:
    def __init__(self, context):
        self.ctx = context
        self.modules = {}
        self.stack = []
        self.events = {}

    def register_module(self, name, module):
        self.modules[name] = module

    def ensure_module_loaded(self, name):
        if name in self.modules:
            return True

        try:
            from core.loaders.module_loader import load_lazy_module
            return bool(load_lazy_module(self, self.ctx, name))
        except:
            return False

    def get_script_dir(self, filepath):
        if "/" not in filepath:
            return "."
        return filepath.rsplit("/", 1)[0]

    def resolve_reference(self, value):
        from core.utils.paths import get_path_value, split_path

        if value in self.ctx.vars:
            return self.ctx.vars[value], True

        parts = split_path(value)
        if len(parts) > 1:
            root_name = parts[0]
            self.ensure_module_loaded(root_name)
            if root_name in self.ctx.vars:
                root_value = self.ctx.vars[root_name]
                nested = get_path_value(root_value, ".".join(parts[1:]))
                return nested, True

            if root_name in self.modules and len(parts) == 2:
                func = self.modules[root_name].get(parts[1])
                if func:
                    return func(self.ctx), True

                getter = self.modules[root_name].get("get")
                if getter:
                    return getter(self.ctx, parts[1]), True

        try:
            return int(value), True
        except:
            return value, False

    def interpolate_text(self, text):
        if not isinstance(text, str):
            return text

        if "{" not in text or "}" not in text:
            return text

        result = ""
        i = 0

        while i < len(text):
            char = text[i]

            if char != "{":
                result += char
                i += 1
                continue

            end = text.find("}", i + 1)
            if end == -1:
                result += char
                i += 1
                continue

            key = text[i + 1:end].strip()
            if not key:
                result += text[i:end + 1]
                i = end + 1
                continue

            resolved, found = self.resolve_reference(key)
            if found:
                result += str(resolved)
            else:
                result += text[i:end + 1]

            i = end + 1

        return result

    # --- VALUE RESOLUTION ---
    def resolve(self, value):
        if isinstance(value, dict):
            if value.get("type") == "expression":
                return self.evaluate_expression(value["value"])

            if value.get("type") == "literal":
                return self.interpolate_text(value.get("value"))

        if isinstance(value, list):
            return [self.resolve(item) for item in value]

        if isinstance(value, str):
            resolved, found = self.resolve_reference(value)
            if found:
                return resolved

            return self.interpolate_text(value)

        return value

    # --- CONDITION EVALUATION ---
    def eval_condition(self, cond):
        from core.parser import Parser

        parser = Parser()
        tokens = parser.tokenize(cond)
        operators = ("==", "is", "!=", ">", "<", "in")

        def eval_operand(text):
            text = text.strip()

            if not text:
                return None

            lowered = text.lower()
            if lowered == "on":
                return True
            if lowered == "off":
                return False

            if text.startswith("(") and text.endswith(")"):
                return self.resolve({
                    "type": "expression",
                    "value": text[1:-1]
                })

            if " " in text:
                return self.evaluate_expression(text)

            return self.resolve(text)

        def eval_simple(left, op, right):
            left = eval_operand(left)
            right = eval_operand(right)
            if op in ["==", "is"]:
                return left == right
            if op == "!=":
                return left != right
            if op == ">":
                return left > right
            if op == "<":
                return left < right
            if op == "in":
                return left in right
            return False

        def eval_segment(segment):
            if not segment:
                return False

            negate = False
            if segment and segment[0] == "not":
                negate = True
                segment = segment[1:]

            if not segment:
                return False

            op_index = -1
            i = 0
            while i < len(segment):
                if segment[i] in operators:
                    op_index = i
                    break
                i += 1

            if op_index == -1:
                value = eval_operand(" ".join(segment))
                result = bool(value)
            else:
                left = " ".join(segment[:op_index])
                op = segment[op_index]
                right = " ".join(segment[op_index + 1:])
                result = eval_simple(left, op, right)

            if negate:
                return not result

            return result

        result = None
        connector = None
        segment = []

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token in ("and", "or"):
                current = eval_segment(segment)

                if result is None:
                    result = current
                elif connector == "and":
                    result = result and current
                elif connector == "or":
                    result = result or current

                connector = token
                segment = []
            else:
                segment.append(token)

            i += 1

        if segment:
            current = eval_segment(segment)

            if result is None:
                result = current
            elif connector == "and":
                result = result and current
            elif connector == "or":
                result = result or current

        return result if result is not None else False

    def resolve_range_value(self, text):
        text = str(text).strip()
        if not text:
            return None

        if text.startswith("(") and text.endswith(")"):
            return self.evaluate_expression(text[1:-1])

        return self.resolve(text)

    def resolve_iterable(self, value):
        # Range: 1-10
        if isinstance(value, str) and "-" in value:
            parts = value.split("-", 1)
            if len(parts) == 2:
                start = self.resolve_range_value(parts[0])
                end = self.resolve_range_value(parts[1])

                try:
                    start = int(start)
                    end = int(end)
                    step = 1 if end >= start else -1
                    return list(range(start, end + step, step))
                except:
                    pass

        val = self.resolve(value)
        if isinstance(val, list):
            return val

        return []

    def collect_block(self, instructions, start_index, allow_else=False):
        block = []
        else_block = []
        current = block
        depth = 1
        i = start_index + 1

        while i < len(instructions):
            instr = instructions[i]

            if instr["type"] in ["if", "foreach", "while", "event"]:
                depth += 1
            elif allow_else and instr["type"] == "else" and depth == 1:
                current = else_block
                i += 1
                continue
            elif instr["type"] == "end":
                depth -= 1
                if depth == 0:
                    break

            current.append(instr)
            i += 1

        return {
            "instructions": block,
            "else": else_block,
            "end": i
        }

    def evaluate_expression(self, expr):
        from core.parser import Parser

        parser = Parser()
        instr = parser.parse_line(expr)

        if instr["type"] == "command":
            module = instr["module"]
            action = instr["action"]

            self.ensure_module_loaded(module)
            module_ref = self.modules.get(module)
            if module_ref is None:
                raise KeyError(module)

            func = module_ref.get(action)
            if func is None:
                raise KeyError("%s.%s" % (module, action))

            positional = instr.get("positional", [])
            args = instr.get("args", {})

            resolved_args = {k: self.resolve(v) for k, v in args.items()}
            resolved_positional = [self.resolve(p) for p in positional]

            return func(self.ctx, *resolved_positional, **resolved_args)

        return None

    def trigger_event(self, module, action):
        key = (module, action)
        if key in self.events:
            for block in self.events[key]:
                self.execute(block)

    def execute_script(self, filepath):
        from core.parser import Parser

        if gc is not None:
            try:
                gc.collect()
            except:
                pass

        parser = Parser()
        script_dir = self.get_script_dir(filepath)

        self.ctx.app_path = script_dir
        self.ctx.data_path = script_dir

        instructions = list(parser.parse_script(filepath))
        try:
            self.execute(instructions)
        finally:
            instructions = None
            if gc is not None:
                try:
                    gc.collect()
                except:
                    pass

    # --- EXECUTION ---
    def execute(self, instructions):
        i = 0
        while i < len(instructions):
            instr = instructions[i]

            if instr["type"] == "set":
                value = self.resolve(instr["value"])
                self.ctx.vars[instr["var"]] = value

            elif instr["type"] == "command":
                module = instr["module"]
                action = instr["action"]

                self.ensure_module_loaded(module)
                if module in self.modules:
                    func = self.modules[module].get(action)

                    if func:
                        try:
                            positional = instr.get("positional", [])
                            args = instr.get("args", {})

                            resolved_args = {
                                k: self.resolve(v) for k, v in args.items()
                            }

                            resolved_positional = [
                                self.resolve(p) for p in positional
                            ]

                            func(self.ctx, *resolved_positional, **resolved_args)

                        except Exception as e:
                            self.ctx.log_exception(e, "Error executing %s.%s" % (module, action))
                    else:
                        self.ctx.log("Unknown action %s.%s" % (module, action), "ERROR")
                else:
                    self.ctx.log("Unknown module %s" % module, "ERROR")

            elif instr["type"] == "if":
                block = self.collect_block(instructions, i, allow_else=True)
                if self.eval_condition(instr["condition"]):
                    self.execute(block["instructions"])
                else:
                    self.execute(block["else"])
                i = block["end"]

            elif instr["type"] == "foreach":
                iterable = self.resolve_iterable(instr["iterable"])
                block = self.collect_block(instructions, i)

                for item in iterable:
                    self.ctx.vars[instr["var"]] = item
                    try:
                        self.execute(block["instructions"])
                    except ContinueLoop:
                        continue
                    except BreakLoop:
                        break
                i = block["end"]

            elif instr["type"] == "while":
                block = self.collect_block(instructions, i)

                while self.eval_condition(instr["condition"]):
                    try:
                        self.execute(block["instructions"])
                    except ContinueLoop:
                        continue
                    except BreakLoop:
                        break
                i = block["end"]

            elif instr["type"] == "event":
                block = self.collect_block(instructions, i)
                key = (instr["module"], instr["action"])

                if key not in self.events:
                    self.events[key] = []

                self.events[key].append(block["instructions"])
                i = block["end"]

            elif instr["type"] == "stop":
                raise BreakLoop()

            elif instr["type"] == "skip":
                raise ContinueLoop()

            i += 1


class BreakLoop(Exception):
    pass


class ContinueLoop(Exception):
    pass
