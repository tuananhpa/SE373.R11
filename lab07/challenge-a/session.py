"""One invocation = one fresh application session. Input JSON on stdin."""
import json
import sys
from agent import run_session, ScriptedModel

if __name__ == "__main__":
    payload = json.load(sys.stdin)
    model = None if payload["live"] else ScriptedModel(payload["actions"])
    result = run_session(payload["user"], payload["memory"], payload["output"],
                         model, payload.get("enabled", True))
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0 if result["status"] == "completed" else 1)
