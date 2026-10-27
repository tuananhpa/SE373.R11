const $ = id => document.getElementById(id);
let current = null;
function element(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function details(parent, title, value) {
  const d = element("details");
  d.append(element("summary", title));
  const full = JSON.stringify(value, null, 2);
  d.append(element("pre", full.length > 30000 ? full.slice(0, 30000) + "\n… Rút gọn hiển thị. Report JSON chứa dữ liệu đầy đủ." : full));
  parent.append(d);
}
function metric(parent, label, value) {
  const el = element("div", undefined, "metric");
  el.append(element("strong", value ?? "Chưa đo"), element("span", label));
  parent.append(el);
}
function section(title) {
  const el = element("article", undefined, "result");
  el.append(element("h3", title)); $("output").append(el); return el;
}
function renderSession(s, index) {
  const el = section(index ? "Session " + index : "Session mới");
  el.append(element("span", s.llm_executed ? "Model thật" : "Scripted offline", "tag"));
  el.append(element("p", s.answer || s.error || s.status, "answer"));
  el.append(element("p", "Chat cũ gửi lại: " + s.history_messages + " · Memory inject: " + s.injected_memory.length));
  if (s.usage) el.append(element("p", "Input tokens: " + s.usage.input_tokens.toLocaleString()));
  details(el, "Memory đã inject vào context", s.injected_memory);
  details(el, "Action và kết quả tool", s.trace);
}
function renderB1(b) {
  const el = section("B1 · Compact xong vẫn tiếp tục đúng việc");
  const metrics = element("div", undefined, "metrics");
  metric(metrics, "Giảm kích thước context", b.context_reduction_percent + "%");
  metric(metrics, "Giảm input tokens thực", b.input_token_saving_percent === null ? null : b.input_token_saving_percent + "%");
  el.append(metrics);
  for (const [name, label] of [["before", "Context đầy đủ"], ["after", "Structured checkpoint"], ["truncated", "Đối chứng cắt tin cũ"]]) {
    const row = b[name];
    el.append(element("p", label + ": " + (row.correct ? "đủ state để tiếp tục" : "thiếu state") + " · " + row.context_chars.toLocaleString() + " ký tự", row.correct ? "ok" : "bad"));
    details(el, label + " / phản hồi", row.answer);
  }
  details(el, "Điều kiện kích hoạt compaction", b.trigger);
}
function renderB2(b) {
  const el = section("B2 · Raw logs so với Code Mode");
  const table = element("table");
  const head = element("tr");
  for (const text of ["Cách chạy", "Tổng input tokens", "Ký tự gửi qua các lượt", "Đúng"]) head.append(element("th", text));
  table.append(head);
  for (const [key, label] of [["raw","read_file từng log"],["code","Script → top 3"]]) {
    const r = b[key], tr = element("tr");
    for (const value of [label, r.usage?.input_tokens?.toLocaleString() ?? "Không gọi LLM", r.context_chars.toLocaleString(), r.correct ? "Có" : "Không"]) tr.append(element("td", value));
    table.append(tr);
  }
  el.append(table);
  el.append(element("p", "Giảm input tokens thực: " + (b.input_token_saving_percent === null ? "chưa đo ở chế độ offline" : b.input_token_saving_percent + "%")));
  el.append(element("p", "Raw log trong context Code Mode: " + (b.code.raw_log_in_context ? "Có" : "Không"), b.code.raw_log_in_context ? "bad" : "ok"));
  details(el, "Top 3 lỗi", b.code.answer.errors);
  details(el, "Trace Code Mode, code model viết và inner tool calls", b.code.trace);
  details(el, "Trace đối chứng đọc raw log", b.raw.trace);
}
function render(report) {
  $("output").replaceChildren();
  const isLive = report.llm_executed;
  $("output").append(element("p", isLive ? "Kết quả model thật · usage từ 9Router" : "Scripted offline · Không chứng minh năng lực LLM, không có số token thật", "tag"));
  if (report.evidence_dir) $("output").append(element("p", "Minh chứng: " + report.evidence_dir));
  if (report.sessions) report.sessions.forEach((s,i) => renderSession(s,i+1));
  else if (report.session) renderSession(report);
  if (report.verification) details($("output"), "Kiểm tra minh chứng", report.verification);
  if (report.b1) renderB1(report.b1);
  if (report.b2) renderB2(report.b2);
}
async function request(path, options) {
  const res = await fetch(path, options);
  const value = await res.json();
  if (!res.ok) throw Error(value.error || "HTTP " + res.status);
  return value;
}
async function refresh() {
  const info = await request("/api/info");
  current = info.challenge;
  $("badge").textContent = "Challenge " + current;
  $("challenge").textContent = "Challenge " + current + (current === "A" ? " / Persistent memory" : " / Context management");
  $("title").textContent = info.title;
  $("description").textContent = current === "A" ? "Một session mới không mang theo chat cũ. Agent nhớ quy ước nhờ memory được lưu, truy xuất và đưa vào context." : "Compact giữ đủ trạng thái để tiếp tục. Code Mode xử lý log trong runtime và chỉ đưa kết quả cần thiết vào context.";
  $("a-controls").hidden = current !== "A"; $("b-controls").hidden = current !== "B";
  if (current === "A") {
    $("memory").replaceChildren();
    if (!info.memory.length) $("memory").textContent = "Chưa lưu quy ước.";
    for (const row of info.memory) {
      const el = element("div", row.key + ": " + row.value, "memory-row");
      el.append(element("small", row.status + " · nguồn " + row.source_session.slice(0,8)));
      $("memory").append(el);
    }
  }
}
async function run(payload) {
  const buttons = [...document.querySelectorAll("button")];
  buttons.forEach(b => b.disabled = true);
  $("download").hidden = true;
  $("status").textContent = $("live").checked ? "Đang gọi model thật. Kịch bản nhiều lượt có thể mất vài phút; trace được lưu trên đĩa." : "Đang chạy kiểm chứng offline…";
  try {
    const job = await request("/api/run", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...payload, live:$("live").checked})});
    $("download").href = "/api/report?id=" + encodeURIComponent(job.id);
    let result;
    do {
      await new Promise(resolve => setTimeout(resolve, 1200));
      result = await request("/api/status?id=" + encodeURIComponent(job.id));
    } while (result.status === "running");
    if (result.status === "failed") throw Error(result.error);
    render(result.result);
    $("download").hidden = false;
    $("status").textContent = "Đã chạy xong. Mở context/trace bên dưới để đối chiếu.";
    await refresh();
  } catch (error) { $("status").textContent = "Lỗi: " + error.message; }
  finally { buttons.forEach(b => b.disabled = false); }
}
$("demo-a").addEventListener("click", () => run({action:"demo"}));
$("session-a").addEventListener("click", () => run({action:"session",user:$("prompt").value,no_memory:$("no-memory").checked}));
$("demo-b").addEventListener("click", () => run({part:$("part").value}));
refresh().catch(e => $("status").textContent = e.message);
