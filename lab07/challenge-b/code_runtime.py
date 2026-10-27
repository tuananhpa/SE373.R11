"""Restricted Python subset for the lab, executed in a short-lived child process."""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ALLOWED_NODES = (ast.Module,ast.Import,ast.alias,ast.Assign,ast.AugAssign,ast.Expr,
    ast.For,ast.If,ast.Call,ast.Name,ast.Load,ast.Store,ast.Attribute,ast.Constant,
    ast.Subscript,ast.BinOp,ast.Add,ast.Mult,ast.Tuple,ast.List,ast.Dict,
    ast.Compare,ast.Eq,ast.NotEq,ast.Gt,ast.Lt,ast.GtE,ast.LtE,ast.UnaryOp,
    ast.Not,ast.USub,ast.BoolOp,ast.And,ast.Or,ast.IfExp,ast.Pass,ast.keyword)
ALLOWED_ATTRS = {"glob","search","Counter","group","most_common","items","get","read","splitlines","close"}

def validate(code):
    if not isinstance(code,str) or len(code) > 10000:
        raise ValueError("Code tối đa 10000 ký tự.")
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError("Cú pháp bị chặn: " + type(node).__name__)
        if isinstance(node,ast.Name) and node.id.startswith("_"):
            raise ValueError("Tên private/dunder bị chặn.")
        if isinstance(node,ast.Attribute) and node.attr not in ALLOWED_ATTRS:
            raise ValueError("Attribute bị chặn: " + node.attr)
        if isinstance(node,ast.Import):
            if any(item.name not in ("glob","re","collections") or item.asname for item in node.names):
                raise ValueError("Chỉ import glob, re, collections không alias.")
    return tree

def run_code(code, root, timeout=5):
    validate(code)
    env = {k:v for k,v in os.environ.items() if k.upper() in
           ("SYSTEMROOT","WINDIR","PATH","TEMP","TMP")}
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run([sys.executable,"-X","utf8","-I",str(Path(__file__).resolve()),
                               "--worker",str(Path(root).resolve())],
                              input=code,text=True,encoding="utf-8",capture_output=True,
                              env=env,timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Code vượt timeout; tiến trình đã dừng.") from exc
    if proc.returncode:
        raise RuntimeError(proc.stderr[-3000:])
    payload = json.loads(proc.stdout)
    return payload["stdout"], payload["trace"]

def worker(code, root):
    import collections
    import io
    import re
    from types import SimpleNamespace
    from logs import Tools
    tools = Tools(root)
    output = []
    size = 0

    def limited_print(*args, sep=" ", end="\n"):
        nonlocal size
        line = sep.join(str(a) for a in args) + end
        size += len(line.encode("utf-8"))
        if size > 16384:
            raise ValueError("stdout vượt 16 KB.")
        output.append(line)

    def safe_open(path):
        return io.StringIO(tools.read_file(path))

    def safe_glob(pattern):
        if pattern != "logs/*.log":
            raise ValueError("Chỉ glob logs/*.log.")
        return tools.list_files()

    modules = {"glob":SimpleNamespace(glob=safe_glob),
               "re":SimpleNamespace(search=re.search),
               "collections":SimpleNamespace(Counter=collections.Counter)}
    def safe_import(name, *args, **kwargs):
        return modules[name]
    builtins = {"__import__":safe_import,"open":safe_open,"print":limited_print,
                "range":range,"len":len,"str":str,"int":int,"sorted":sorted}
    exec(compile(validate(code), "<lab-code>", "exec"), {"__builtins__":builtins})
    return {"stdout":"".join(output),"trace":tools.trace}

if __name__ == "__main__":
    # -I excludes this script directory, add back only our local trusted modules.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        print(json.dumps(worker(sys.stdin.read(), sys.argv[2]), ensure_ascii=True))
    except Exception as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
