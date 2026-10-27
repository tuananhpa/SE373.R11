"""Re-check saved evidence without running a model or generated code."""
import json
import sys
from pathlib import Path
from compaction import compact, evaluate
from logs import Tools, aggregate
from runtime import sum_usage

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def verify(root):
    root = Path(root)
    checks = {}
    try:
        top = read(root/"report.json")
        if (root/"b1").exists():
            folder = root/"b1"
            report = read(folder/"report.json")
            checkpoint = read(folder/"checkpoint.json")
            checks["b1_checkpoint_from_archive"] = compact(read(folder/"archive.json")) == checkpoint
            checks["b1_full_and_compact_correct"] = evaluate(report["before"]["answer"]) and evaluate(report["after"]["answer"])
            checks["b1_truncation_loses_state"] = not evaluate(report["truncated"]["answer"])
            for mode in ("before","after","truncated"):
                prompt = (folder/f"{mode}.input.txt").read_text(encoding="utf-8")
                checks[f"b1_{mode}_chars"] = len(prompt) == report[mode]["context_chars"]
                if top["llm_executed"]:
                    checks[f"b1_{mode}_answer"] = read(folder/f"{mode}.answer.json") == report[mode]["answer"]
                    events = [json.loads(line) for line in (folder/f"{mode}.events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
                    checks[f"b1_{mode}_usage"] = [e["usage"] for e in events if e.get("type") == "turn.completed"] == [report[mode]["usage"]]
            checks["b1_raw_archived_not_in_checkpoint"] = "RAW_LOG_MARKER" not in json.dumps(checkpoint)
        if (root/"b2").exists():
            folder = root/"b2"
            report = read(folder/"report.json")
            tools = Tools(folder)
            paths = tools.list_files()
            expected = aggregate([tools.read_file(p) for p in paths])
            checks["b2_expected_from_logs"] = expected == read(folder/"expected.json")
            for mode in ("raw","code"):
                result = read(folder/mode/"result.json")
                checks[f"b2_{mode}_answer"] = result["answer"]["errors"] == expected
                checks[f"b2_{mode}_report"] = report[mode] == result
                prompts = sorted((folder/mode).glob("step-*.input.txt"))
                checks[f"b2_{mode}_chars"] = sum(len(p.read_text(encoding="utf-8")) for p in prompts) == result["context_chars"]
                if mode == "code":
                    checks["b2_no_raw_in_code_context"] = not any("RAW_LOG_MARKER" in p.read_text(encoding="utf-8") for p in prompts)
                    reads = {e["path"] for t in result["trace"] for e in t.get("inner_tool_calls",[]) if e["tool"] == "read_file"}
                    checks["b2_code_read_all_files"] = reads == set(paths)
                    outputs = [e["result"] for e in result["trace"] if e["action"]["tool"] == "run_code"]
                    expected_stdout = "\n".join(f"{r['code']} {r['count']}" for r in expected) + "\n"
                    checks["b2_only_top_three_stdout"] = outputs == [expected_stdout]
                if top["llm_executed"]:
                    usages = []
                    for event_file in sorted((folder/mode).glob("step-*.events.jsonl")):
                        events = [json.loads(line) for line in event_file.read_text(encoding="utf-8").splitlines() if line.strip()]
                        usages.extend(e["usage"] for e in events if e.get("type") == "turn.completed")
                    checks[f"b2_{mode}_usage"] = len(usages) == result["model_calls"] and sum_usage(usages) == result["usage"]
                    actions = [read(p) for p in sorted((folder/mode).glob("step-*.answer.json"))]
                    checks[f"b2_{mode}_actions"] = actions == [e["action"] for e in result["trace"]]
            if top["llm_executed"]:
                saving = round((1-report["code"]["usage"]["input_tokens"]/report["raw"]["usage"]["input_tokens"])*100,2)
                checks["b2_saving_recomputed"] = saving == report["input_token_saving_percent"]
            else:
                checks["offline_no_fake_usage"] = all(report[m]["usage"] is None for m in ("raw","code"))
        checks["contains_challenge_evidence"] = (root/"b1").exists() or (root/"b2").exists()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        checks["readable_and_complete"] = False
        return {"passed":False,"checks":checks,"error":str(exc)}
    return {"passed":all(checks.values()),"checks":checks,
            "note":"Kiểm tra nhất quán artifact, không phải chữ ký chống giả mạo hoặc đánh giá ngữ nghĩa tổng quát."}

if __name__ == "__main__":
    result = verify(sys.argv[1] if len(sys.argv)>1 else Path(__file__).parent/"evidence"/"live-validation")
    print(json.dumps(result,ensure_ascii=True,indent=2))
    sys.exit(0 if result["passed"] else 1)
