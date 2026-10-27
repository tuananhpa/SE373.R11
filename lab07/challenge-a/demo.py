import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from memory import MemoryStore
from runtime import save

QUESTION = "Dự án hiện dùng cơ chế authentication nào?"
SCENARIO = [
    ("Hãy nhớ quy ước dự án: authentication dùng JWT.",
     [{"tool":"remember_memory","key":"auth","value":"JWT","evidence":"authentication dùng JWT"},
      {"tool":"final","answer":"Đã lưu quy ước authentication dùng JWT."}]),
    (QUESTION,[{"tool":"read_memory"},{"tool":"final","answer":"Dự án dùng JWT."}]),
    ("Chốt thay đổi: authentication dùng session cookie thay cho JWT. Hãy nhớ quy ước mới.",
     [{"tool":"remember_memory","key":"auth","value":"session cookie thay cho JWT",
       "evidence":"authentication dùng session cookie thay cho JWT"},
      {"tool":"final","answer":"Đã thay quy ước cũ bằng session cookie."}]),
    (QUESTION,[{"tool":"final","answer":"Dự án dùng session cookie thay cho JWT."}]),
    (QUESTION,[{"tool":"final","answer":"Chưa có thông tin quy ước authentication trong session này."}]),
]

def verify(root):
    root = Path(root)
    results = [json.loads((root / f"session-{i}" / "result.json").read_text(encoding="utf-8"))
               for i in range(1,6)]
    rows = MemoryStore(root / "memory.json").records()
    checks = {
        "five_fresh_sessions":len({r["session"] for r in results}) == 5 and all(r["history_messages"] == 0 for r in results),
        "all_completed":all(r["status"] == "completed" for r in results),
        "jwt_injected_session_2":any(r["key"] == "auth" and "JWT" in r["value"] for r in results[1]["injected_memory"]),
        "cookie_injected_session_4":any(r["key"] == "auth" and "cookie" in r["value"].lower() for r in results[3]["injected_memory"]),
        "old_revision_superseded":any(r["status"] == "superseded" and r["superseded_by"] in
                                    [n["id"] for n in rows if n["status"] == "active"] for r in rows),
        "one_active_auth":sum(r["status"] == "active" and r["key"] == "auth" for r in rows) == 1,
        "control_has_no_memory":not results[4]["injected_memory"] and not results[4]["memory_enabled"],
        "write_tools_executed":all(any(e["action"]["tool"] == "remember_memory" for e in results[i]["trace"])
                                   for i in (0,2)),
        "answers_match_revisions":"jwt" in results[1].get("answer","").lower()
                                  and "cookie" in results[3].get("answer","").lower(),
    }
    return {"passed":all(checks.values()),"checks":checks,
            "note":"Kiểm tra cấu trúc và từ khóa; đọc answer/trace để đánh giá ngữ nghĩa, nhất là đối chứng."}

def run_demo(root, live=False):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    sessions = []
    for i, (user, actions) in enumerate(SCENARIO, 1):
        payload = {"user":user,"actions":actions,"live":live,"enabled":i != 5,
                   "memory":str(root / "memory.json"),"output":str(root / f"session-{i}")}
        proc = subprocess.run([sys.executable,"-B",str(Path(__file__).with_name("session.py"))],
                              input=json.dumps(payload), text=True, encoding="utf-8",
                              errors="replace", capture_output=True, timeout=450)
        if not proc.stdout.strip():
            raise RuntimeError("Session process failed: " + proc.stderr[-2000:])
        result = json.loads(proc.stdout)
        sessions.append(result)
        if proc.returncode or result["status"] != "completed":
            save(root / "report.json", {"status":"failed","llm_executed":live,"sessions":sessions})
            raise RuntimeError("Session thất bại, xem " + str(root / f"session-{i}" / "result.json"))
    report = {"status":"completed","llm_executed":live,"mode":"live" if live else "scripted_offline",
              "sessions":sessions,"verification":verify(root),"evidence_dir":str(root)}
    save(root / "report.json", report)
    return report

def timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Challenge A: 5 session độc lập; mặc định offline.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.verify) if args.verify else run_demo(
        args.output or Path(__file__).parent / "evidence" / timestamp(), args.live)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    sys.exit(0 if report.get("passed", report.get("verification",{}).get("passed",False)) else 1)
