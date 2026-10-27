"""Single-writer JSON memory with revision provenance and atomic replacement."""
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

class MemoryStore:
    def __init__(self, path):
        self.path = Path(path)

    def records(self):
        if not self.path.exists():
            return []
        try:
            rows = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise ValueError("Memory phải là danh sách.")
            for row in rows:
                if not isinstance(row, dict) or not all(k in row for k in
                    ("id","key","value","status","source_session","created_at","superseded_by","evidence")):
                    raise ValueError("Memory record thiếu metadata.")
                if row["status"] not in ("active", "superseded"):
                    raise ValueError("Trạng thái memory sai.")
            active_keys = [r["key"] for r in rows if r["status"] == "active"]
            if len(active_keys) != len(set(active_keys)):
                raise ValueError("Nhiều revision active cùng key.")
            return rows
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError("Memory hỏng; giữ nguyên file để kiểm tra.") from exc

    def active(self):
        return [row for row in self.records() if row["status"] == "active"]

    def remember(self, key, value, user, session, evidence):
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key):
            raise ValueError("Key chỉ gồm chữ thường, số, _ hoặc -; tối đa 64 ký tự.")
        if not all(isinstance(s, str) and s.strip() for s in (value, user, session, evidence)):
            raise ValueError("Value, nguồn và evidence không được trống.")
        if len(value) > 2000 or len(evidence) > 4000 or evidence not in user:
            raise ValueError("Evidence phải trích nguyên văn từ yêu cầu hiện tại.")
        rows = self.records()
        record = {"id":uuid.uuid4().hex, "key":key, "value":value, "evidence":evidence,
                  "source_session":session, "created_at":datetime.now(timezone.utc).isoformat(),
                  "status":"active", "superseded_by":None}
        for row in rows:
            if row["key"] == key and row["status"] == "active":
                row["status"] = "superseded"
                row["superseded_by"] = record["id"]
        rows.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".memory-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(rows, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return record
