from pathlib import Path
from demo import run_demo, timestamp

def info():
    return {"challenge":"B","title":"Giữ điều cần thiết"}

def perform(payload):
    part = payload.get("part","all")
    if part not in ("all","b1","b2"):
        raise ValueError("Chọn all, b1 hoặc b2.")
    return run_demo(Path(__file__).parent/"data"/"ui"/timestamp(),payload.get("live",False),part)
