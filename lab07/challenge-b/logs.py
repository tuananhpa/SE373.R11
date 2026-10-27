import re
from collections import Counter
from pathlib import Path

EXPECTED = [{"code":"ERR_DB_TIMEOUT","count":180},
            {"code":"ERR_AUTH_EXPIRED","count":120},
            {"code":"ERR_RATE_LIMIT","count":60}]
PATTERN = re.compile(r" ERROR \S+ (ERR_[A-Z0-9_]+)\b")

def generate_logs(root):
    root = Path(root)
    folder = root / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    for file_index in range(6):
        lines = []
        for i in range(400):
            code = ("ERR_DB_TIMEOUT" if i < 30 else "ERR_AUTH_EXPIRED" if i < 50
                    else "ERR_RATE_LIMIT" if i < 60 else "ERR_NETWORK" if i < 65 else None)
            prefix = f"2026-10-27T00:{file_index:02}:{i % 60:02}Z"
            if code:
                line = f"{prefix} ERROR worker-{file_index} {code} request={i}"
            else:
                line = f"{prefix} INFO worker-{file_index} RAW_LOG_MARKER request={i} completed latency=12ms"
            lines.append(line + "\n")
        lines += ["2026-10-27 WARN worker ERR_FAKE ignore\n",
                  "2026-10-27 ERROR missing-code malformed\n"]
        (folder / f"service-{file_index}.log").write_text("".join(lines), encoding="utf-8")
    return EXPECTED

class Tools:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.trace = []

    def list_files(self):
        result = sorted(p.relative_to(self.root).as_posix()
                        for p in (self.root / "logs").glob("*.log"))
        if len(result) > 100:
            raise ValueError("Demo giới hạn 100 file.")
        self.trace.append({"tool":"list_files","result":result})
        return result

    def read_file(self, path):
        if not isinstance(path, str):
            raise ValueError("Path phải là chuỗi.")
        file = (self.root / path).resolve()
        logs = (self.root / "logs").resolve()
        if not file.is_relative_to(logs) or file.suffix != ".log" or not file.is_file():
            raise ValueError("Chỉ được đọc file .log bên trong logs/.")
        if file.stat().st_size > 1_000_000:
            raise ValueError("Mỗi file tối đa 1 MB.")
        content = file.read_text(encoding="utf-8")
        self.trace.append({"tool":"read_file","path":path,"bytes":len(content.encode("utf-8"))})
        return content

def aggregate(texts):
    codes = Counter()
    for text in texts:
        for line in text.splitlines():
            match = PATTERN.search(line)
            if match:
                codes[match.group(1)] += 1
    return [{"code":code,"count":count} for code,count in codes.most_common(3)]
