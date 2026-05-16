# /os/core/context.py
class Context:
    def __init__(self, app_path="/sd/main", data_path="/sd/main"):
        self.vars = {}       # Stores script variables
        self.app_path = app_path
        self.data_path = data_path
        self.logs = []
        self.max_logs = 64

    def log(self, message, level="INFO"):
        line = f"[{level}] {message}"
        self.logs.append(line)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        print(line)

    def log_exception(self, error, prefix="Unhandled error"):
        message = str(error)
        self.log("%s: %s" % (prefix, message), "ERROR")
        try:
            import sys
            import traceback
            traceback.print_exception(type(error), error, sys.exc_info()[2])
        except:
            pass
