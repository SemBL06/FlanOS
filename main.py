import sys

if "/os" not in sys.path:
    sys.path.insert(0, "/os")
if "os" not in sys.path:
    sys.path.insert(0, "os")

namespace = {
    "__name__": "__main__",
    "__file__": "/os/main.py"
}

with open("/os/main.py", "r") as f:
    code = f.read()

exec(code, namespace)
