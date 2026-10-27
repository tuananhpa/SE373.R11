from pathlib import Path
from agent import run_session
from demo import run_demo, timestamp
from memory import MemoryStore

ROOT = Path(__file__).parent / "data" / "ui"

def info():
    return {"challenge":"A","title":"Quy ước đi cùng dự án",
            "memory":MemoryStore(ROOT/"custom"/"memory.json").records()}

def perform(payload):
    live = payload.get("live",False)
    if payload.get("action","demo") == "demo":
        return run_demo(ROOT/timestamp(),live)
    if payload.get("action") == "session":
        if not live:
            raise ValueError("Câu nói tự nhập cần bật model thật. Offline chỉ chạy kịch bản có sẵn.")
        result = run_session(payload.get("user",""),ROOT/"custom"/"memory.json",ROOT/"custom"/timestamp(),
                             enabled=not payload.get("no_memory",False))
        if result["status"] == "failed":
            raise RuntimeError(result["error"])
        return result
    raise ValueError("Action không hợp lệ.")
