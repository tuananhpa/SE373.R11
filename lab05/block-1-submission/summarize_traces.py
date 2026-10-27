"""Summarize real trace evidence with line numbers; never manufacture trace events."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
lines = ["# Kết quả trace thực tế", "", "Nội dung dưới đây được trích từ trace có trên đĩa. Đối chiếu câu trả lời với kỳ vọng trong analysis.md.", ""]
missing = []
for stage in ["stage-00-chat", "stage-01-files", "stage-02-skills"]:
    cases = ["A"] if stage == "stage-00-chat" else ["A", "B", "A-renamed", "B-renamed", "missing"]
    for case in cases:
        index = root / stage / "traces" / f"{case}-index.json"
        lines.extend([f"## {stage} / {case}", ""])
        if not index.exists():
            missing.append(f"{stage}/{case}")
            lines.extend(["Chưa có index của lượt chạy hoàn tất.", ""])
            continue
        name = json.loads(index.read_text(encoding="utf-8"))["trace"]
        trace = index.parent / name
        events = [json.loads(row) for row in trace.read_text(encoding="utf-8").splitlines() if row.strip()]
        lines.append(f"Trace: `{stage}/traces/{name}`")
        lines.append("")
        for number, event in enumerate(events, 1):
            if event.get("type") == "tool_finished":
                result = event.get("result", {})
                path = result.get("path", "") if isinstance(result, dict) else ""
                ok = result.get("ok") if isinstance(result, dict) else None
                lines.append(f"- Dòng {number}: `{event.get('tool_name')}`, path `{path}`, ok `{ok}`.")
            if event.get("type") == "model_request":
                messages = event.get("snapshot", {}).get("messages", [])
                loaded = [message.get("name", "tool") for message in messages if message.get("role") == "tool"]
                lines.append(f"- Dòng {number}: model request, {len(messages)} messages; {len(loaded)} tool results trong context.")
            if event.get("type") == "run_completed":
                lines.extend(["", f"Câu trả lời cuối (dòng {number}):", "", str(event.get("answer", "Không có answer trong event; xem messages.")), ""])
        lines.append("")
lines.extend(["## Trạng thái", "", "Đủ index của mọi lượt chạy." if not missing else "Còn thiếu: " + ", ".join(missing), ""])
output = root / "trace-results.md"
output.write_text("\n".join(lines), encoding="utf-8")
print(output)
if missing:
    raise SystemExit(1)
