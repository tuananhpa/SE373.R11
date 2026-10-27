"""Structured checkpoint from typed harness events; no LLM summarization call."""
import copy

STATE = {
    "goal":"Fix refresh-token race condition",
    "error":"ERR_REFRESH_RACE during concurrent refresh",
    "current_state":"handler implemented; concurrent refresh test failing",
    "constraints":["keep API backward compatible","do not log refresh tokens"],
    "findings":["failure occurs during concurrent refresh"],
    "failed_attempts":["increasing token TTL did not help","client retry did not help"],
    "files":["auth.ts","session.ts","auth.test.ts"],
    "next_action":"inspect locking around refresh",
}
LIST_FIELDS = {"constraints","findings","failed_attempts","files"}

def make_history():
    events = [{"kind":key,"value":copy.deepcopy(value)} for key,value in STATE.items()]
    for i in range(32):
        events.append({"kind":"tool_output","tool":"run_tests","value":
                       ("RAW_LOG_MARKER test pass debug detail " + str(i) + "\n") * 120})
    events.append({"kind":"user","value":"Tiếp tục điều tra. Nhắc lại lỗi, constraints, cách đã thử, files và bước tiếp."})
    return events

def compact(events):
    checkpoint = {}
    for event in events:
        kind = event["kind"]
        if kind not in STATE:
            continue
        if kind in LIST_FIELDS:
            values = event["value"]
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ValueError("Checkpoint list không hợp lệ.")
            checkpoint[kind] = list(dict.fromkeys(checkpoint.get(kind,[]) + values))
        else:
            if not isinstance(event["value"], str):
                raise ValueError("Checkpoint scalar không hợp lệ.")
            checkpoint[kind] = event["value"]
    if set(checkpoint) != set(STATE):
        raise ValueError("Thiếu trường checkpoint; không tiếp tục với state không đầy đủ.")
    return checkpoint

def offline_continue(context):
    # Test double extracts only what its supplied context contains.
    if isinstance(context, dict):
        return copy.deepcopy(context)
    found = {}
    for event in context:
        if event.get("kind") in STATE:
            found[event["kind"]] = copy.deepcopy(event["value"])
    return found

def evaluate(answer):
    return all(answer.get(key) == value for key,value in STATE.items())
